# using flask_restful 
from flask import Flask, request, jsonify
from flask_restful import Resource, Api

from flask_cors import CORS

import os
import base64
import json
import logging

# --- init logging ---
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("app")

# Resolve paths first so CsvChecker uses the correct CSV location
APP_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_CSV_PATH = os.path.join(APP_DIR, 'results.csv')
os.environ['RESULTS_CSV'] = RESULTS_CSV_PATH  # must be set BEFORE importing CsvChecker

# importing scraper logic
from scrapeRA import runScrape

# CSV cache helpers (with UPSERT)
import CsvChecker
from CsvChecker import find_car_in_csv, upsert_car_data

# Verify CsvChecker sees the path we expect
log.info(f"CsvChecker.RESULTS_CSV -> {CsvChecker.RESULTS_CSV}")

# need to manually do stuff with the opencv library because the program is unable to resize the image sent from the frontend,
# so this feeds in the image as a NumPy array image instead of a file path
import cv2  # noqa: F401  (kept if you need cv2 elsewhere)
import numpy as np  # noqa: F401
import openai

from dotenv import load_dotenv

# --- init OpenAI client ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key
client = openai.OpenAI()

# creating the flask app
app = Flask(__name__)
api = Api(app)
CORS(app, resources={r'/*': {'origins': '*'}})

UPLOAD_FOLDER = os.path.join(APP_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def _list_or_semicolon_string(v):
    """Return list for API response; splits semicolon-delimited strings too."""
    if v is None:
        return []
    if isinstance(v, list):
        return v
    if isinstance(v, str) and ';' in v:
        return [s.strip() for s in v.split(';') if s.strip()]
    return [str(v)] if isinstance(v, (int, float, str)) else []

def _titlecase_column_name(key: str) -> str:
    return key.replace('_', ' ').title()

class GetInfo(Resource):
    def post(self):
        if 'image' not in request.files:
            return {'error': 'No image file provided'}, 400

        image_file = request.files['image']
        if image_file.filename == '':
            return {'error': 'Empty filename'}, 400

        # read image file from request without saving to disk
        image_bytes = image_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # optional brand filters passed by frontend
        filters_raw = request.form.get("filters", "[]")
        try:
            filters = json.loads(filters_raw) if isinstance(filters_raw, str) else (filters_raw or [])
        except Exception:
            filters = []
        log.info(f"Received filters: {filters}")

        prompt = """
        You are an OCR and document parsing assistant.
        From this repair order image, extract ONLY the following and respond as a normal string in this format:
        <year> <make> <model> <engine>
        Example: 2020 Toyota Corolla 1.8L L4
        """

        # Send image + prompt to GPT-4o-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}
                        }
                    ]
                }
            ],
            max_tokens=200
        )

        car_string = (response.choices[0].message.content or "").strip()
        if not car_string:
            return {'error': 'Failed to parse vehicle info from image'}, 422

        log.info(f"OCR car string: {car_string}")

        # 1) CSV cache lookup (whatever fields already known)
        cached = None
        try:
            cached = find_car_in_csv(car_string)  # dict of columns (no 'Car') or False
        except Exception as e:
            log.error(f"[CSV READ ERROR] {e}")

        # 2) Scrape fresh data (fill any missing/new fields)
        try:
            scraped = runScrape(car_string, filters)
            log.info(f"Scraped raw: {scraped}")

            if not isinstance(scraped, dict) or not scraped:
                # If scraper returns nothing, fall back to cache if present
                if cached:
                    return jsonify({
                        'car': car_string,
                        'oil_filters': _list_or_semicolon_string(cached.get('Oil Filters')),
                        'oil_types': _list_or_semicolon_string(cached.get('Oil Types')),
                        'oil_capacity': cached.get('Oil Capacity', 'Unknown'),
                        'source': 'cache'
                    })
                return {'error': 'No results from scraper and no cache available'}, 502

            # Map scraper keys to CSV column names
            key_map = {
                'oil_filters': 'Oil Filters',
                'oil_types': 'Oil Types',
                'oil_capacity': 'Oil Capacity',
                'engine_air_filters': 'Engine Air Filters',
                'cabin_air_filters': 'Cabin Air Filters',
                'fuel_filters': 'Fuel Filters',
                'transmission_filters': 'Transmission Filters'
            }

            # Prepare values for UPSERT (CSV wants strings; join lists with '; ')
            to_upsert = {}
            for k, v in scraped.items():
                col = key_map.get(k, _titlecase_column_name(k))
                if isinstance(v, list):
                    to_upsert[col] = '; '.join(map(str, v))
                else:
                    to_upsert[col] = '' if v is None else str(v)

            # 3) Merge into CSV
            merged = upsert_car_data(car_string, to_upsert)  # returns full row (minus 'Car')
            log.info(f"Upserted row for {car_string}: {merged}")

            # Build top-level response compatible with your frontend
            oil_filters_resp = scraped.get('oil_filters') or merged.get('Oil Filters', '')
            oil_types_resp = scraped.get('oil_types') or merged.get('Oil Types', '')
            oil_capacity_resp = scraped.get('oil_capacity', merged.get('Oil Capacity', 'Unknown'))

            return jsonify({
                'car': car_string,
                'oil_filters': _list_or_semicolon_string(oil_filters_resp),
                'oil_types': _list_or_semicolon_string(oil_types_resp),
                'oil_capacity': oil_capacity_resp,
                'source': ('scraped+cache' if cached else 'scraped')
            })

        except Exception as e:
            log.error(f"[SCRAPE ERROR] {e}")
            # If scrape fails, return cache if we have anything
            if cached:
                return jsonify({
                    'car': car_string,
                    'oil_filters': _list_or_semicolon_string(cached.get('Oil Filters')),
                    'oil_types': _list_or_semicolon_string(cached.get('Oil Types')),
                    'oil_capacity': cached.get('Oil Capacity', 'Unknown'),
                    'source': 'cache'
                })
            return {'error': 'Scrape failed and no cache available'}, 503

# adding the defined resources along with their corresponding urls
api.add_resource(GetInfo, '/ReadInfo')

# driver function
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
