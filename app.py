# using flask_restful 
from flask import Flask, request, jsonify
from flask_restful import Resource, Api

from flask_cors import CORS

import os
import base64
import json

# importing scraper logic
from scrapeRA import runScrape

# CSV cache helpers
from CsvChecker import find_car_in_csv, append_car_to_csv

# need to manually do stuff with the opencv library because the program is unable to resize the image sent from the frontend,
# so this feeds in the image as a NumPy array image instead of a file path
import cv2
import numpy as np
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

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# THIS ONE USES THE ACTUAL AI LLM OCR METHOD
# After reading it out, it then scrapes RockAuto (if not cached)
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
        filters_json = request.form.get("filters", "[]")

        # Prompt to extract a single normalized line: "<year> <make> <model> <engine>"
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

        # Once LLM extracts the year make and model, try CSV cache first
        car_string = (response.choices[0].message.content or "").strip()
        if not car_string:
            return {'error': 'Failed to parse vehicle info from image'}, 422

        # 1) CSV cache lookup
        try:
            cached = find_car_in_csv(car_string)
            if cached:
                # Return cached result immediately
                return jsonify({
                    'car': car_string,
                    'oil_filters': cached.get('Oil Filters', ''),
                    'oil_types': cached.get('Oil Types', ''),
                    'oil_capacity': cached.get('Oil Capacity', 'Unknown'),
                    'source': 'cache'
                })
        except Exception as e:
            # Cache read error should not prevent scraping; log and continue
            print(f"[CSV CACHE READ ERROR] {e}")

        # 2) Cache miss → scrape, then append to CSV and return
        try:
            results = runScrape(car_string, filters_json)
            # Expecting results like:
            # {
            #   'oil_filters': ['Brand: Part', ...] or 'Brand: Part; Brand2: Part2',
            #   'oil_types': ['5w-20', '0w-20'] or '5w-20; 0w-20',
            #   'oil_capacity': '5.4 quarts'
            # }

            # Normalize outgoing fields to CSV-friendly strings
            oil_filters = results.get('oil_filters', [])
            oil_types = results.get('oil_types', [])
            oil_capacity = results.get('oil_capacity', 'Unknown')

            if isinstance(oil_filters, list):
                oil_filters_csv = '; '.join(oil_filters)
            else:
                oil_filters_csv = str(oil_filters)

            if isinstance(oil_types, list):
                oil_types_csv = '; '.join(oil_types)
            else:
                oil_types_csv = str(oil_types)

            # Append to CSV (will no-op if duplicate)
            try:
                append_car_to_csv(
                    car_string,
                    oil_filters=oil_filters_csv,
                    oil_types=oil_types_csv,
                    oil_capacity=oil_capacity
                )
            except Exception as e:
                # CSV write error shouldn't block response; log it
                print(f"[CSV APPEND ERROR] {e}")

            # Return scraped result
            return jsonify({
                'car': car_string,
                'oil_filters': oil_filters if isinstance(oil_filters, list) else oil_filters_csv,
                'oil_types': oil_types if isinstance(oil_types, list) else oil_types_csv,
                'oil_capacity': oil_capacity,
                'source': 'scraped'
            })

        except Exception as e:
            print(f"[SCRAPE ERROR] {e}")
            return {'error': 'Scrape failed'}, 503

# adding the defined resources along with their corresponding urls
api.add_resource(GetInfo, '/ReadInfo')

# driver function
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
