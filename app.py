# using flask_restful
from flask import Flask, request, jsonify
from flask_restful import Resource, Api

from flask_cors import CORS

import re
import os

#importing scraper logic
from scrapeRA import runScrape

#need to manually do stuff with the opencv library because the program is unable to resize the image sent from the frontend, so this feeds in the image as a NumPy array image instead of a file path
import cv2
import numpy as np
import base64
import openai

from dotenv import load_dotenv

#---init OpenAI client---
#loading env file with API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

openai.api_key = api_key

# Initialize client (make sure OPENAI_API_KEY is in your environment variables)
client = openai.OpenAI()

# creating the flask app
app = Flask(__name__)
# creating an API object
api = Api(app)
CORS(app, resources={r'/*': {'origins': '*'}})

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# making a class for a particular resource
# the get, post methods correspond to get and post requests
# they are automatically mapped by flask_restful.
# other methods include put, delete, etc.
#THIS ONE USES THE ACTUAL AI LLM OCR METHOD
#After reading it out, it then scraped RockAuto
class GetInfo(Resource):
    def post(self):
        if 'image' not in request.files:
            return {'error': 'No image file provided'}, 400

        image_file = request.files['image']
        if image_file.filename == '':
            return {'error': 'Empty filename'}, 400
        
        #read image file from request without saving to disk
        image_bytes = image_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        #checking if filter came through
        filters_json = request.form.get("filters", "[]")
        print(filters_json)

        # Define the request
        prompt = """
        You are an OCR and document parsing assistant.
        From this repair order image, extract ONLY the following and respond as a normal string in this format: <year> <make> <model> <engine> (e.g. 2020 Toyota Corolla 1.8L L4)
        """

        # Send image + prompt to GPT-4o-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                },
                {
                    "role":"user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=200
        )

        # Once LLM extracts the year make and model, send it to the scraper
        gpt_output = response.choices[0].message.content.strip()
        print(gpt_output)

        ##SENDING TO SCRAPER###
        try:
            results = runScrape(gpt_output, filters_json)
            data = jsonify(results)
            return data
        except Exception as e:
            print(e)
            return "Error", 503

# adding the defined resources along with their corresponding urls
api.add_resource(GetInfo, '/ReadInfo')

# driver function
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
