# using flask_restful
from flask import Flask, jsonify, request
from flask_restful import Resource, Api

from flask_cors import CORS

import re
import os

#need to manually do stuff with the opencv library because the program is unable to resize the image sent from the frontend, so this feeds in the image as a NumPy array image instead of a file path
import cv2
import numpy as np

###-----REMOVE THIS WHEN IMPORTING DIFFERENT OCR APPROACH----###
#importing easyocr for reading the scanned VIN number
import easyocr
reader = easyocr.Reader(['en'])

###----------------------------------###

# creating the flask app
app = Flask(__name__)
# creating an API object
api = Api(app)
CORS(app, resources={r'/*': {'origins': '*'}})

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class ImageOCR(Resource):
    def post(self):
        if 'image' not in request.files:
            return {'error': 'No image file provided'}, 400

        image_file = request.files['image']
        if image_file.filename == '':
            return {'error': 'Empty filename'}, 400
        
        file_bytes = np.frombuffer(image_file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if  img is None:
            return {'error': 'Could not decode image'}, 400

        #this should be deleted since the reader is not reading from the filestore now
        file_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
        image_file.save(file_path)

        try:
            result = reader.readtext(img)
            
            output_string = ""
            vin_regex = r'[A-HJ-NPR-Z0-9]{17}' #this regular expression allows us to search the output string for characters that fit the VIN number pattern

            for (bbox, text, prob) in result:
                output_string += text

            output_string = output_string.replace(" ", "") #remove spaces
            
            output = re.findall(vin_regex, output_string.upper())
            return {'VINTEXT': output, 'string': output_string}, 200
        
        except Exception as e:
            return {'error': str(e)}, 500

# making a class for a particular resource
# the get, post methods correspond to get and post requests
# they are automatically mapped by flask_restful.
# other methods include put, delete, etc.


# a resource to get the text from the repair order
class VINNum(Resource):
    
    def get(self):
        result = reader.readtext('./Sample.jpg') # this is part of the easyOCR library, remove when implementing other approach
        output_string = ""
        vin_regex = r'[A-HJ-NPR-Z0-9]{17}' #this regular expression allows us to search the output string for characters that fit the VIN number pattern

        for (bbox, text, prob) in result:
            output_string += text

        output_string = output_string.replace(" ", "") #remove spaces
        
        output = re.findall(vin_regex, output_string.upper())
        return jsonify({'VINTEXT': output, 'string': output_string})



class Hello(Resource):
    def get(self):
        return "API Call worked"

# adding the defined resources along with their corresponding urls
api.add_resource(VINNum, '/VIN')
api.add_resource(Hello, '/')

api.add_resource(ImageOCR, '/ReadVIN')


# driver function
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
