# using flask_restful
from flask import Flask, jsonify, request
from flask_restful import Resource, Api

import re

###-----REMOVE THIS WHEN IMPORTING DIFFERENT OCR APPROACH----###
#importing easyocr for reading the scanned VIN number
import easyocr
reader = easyocr.Reader(['en'])

###----------------------------------###

# creating the flask app
app = Flask(__name__)
# creating an API object
api = Api(app)

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


# adding the defined resources along with their corresponding urls
api.add_resource(Hello, '/')
api.add_resource(VINNum, '/VIN')


# driver function
if __name__ == '__main__':

    app.run(debug = True)