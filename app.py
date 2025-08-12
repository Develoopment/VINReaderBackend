# using flask_restful
from flask import Flask, jsonify, request
from flask_restful import Resource, Api

from flask_cors import CORS
import csv
import time
import os
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import os
import json

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

# making a class for a particular resource
# the get, post methods correspond to get and post requests
# they are automatically mapped by flask_restful.
# other methods include put, delete, etc.
#THIS ONE USES THE ACTUAL AI LLM OCR METHOD
class ImageOCR(Resource):
    def post(self):
        if 'image' not in request.files:
            return {'error': 'No image file provided'}, 400

        image_file = request.files['image']
        if image_file.filename == '':
            return {'error': 'Empty filename'}, 400
        
        #read image file from request without saving to disk
        image_bytes = image_file.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # Define the request
        prompt = """
        You are an OCR and document parsing assistant.
        From this repair order image, extract ONLY the following and respond as a normal string:
        {
        "year": "<year>",
        "make": "<make>",
        "model": "<model>",
        "engine": "<engine>"
        }
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

        # Print the model's output
        gpt_output = response.choices[0].message.content.strip()
        print(gpt_output)
        #data = json.loads(gpt_output)
        print(gpt_output)

        #return actual json
        return "{'name':'saka'}", 200

# a resource to get the text from the repair order
class VINNum(Resource):
    
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


class Hello(Resource):
    def get(self):
        return "API Call worked"
class DataScrape(Resource)
    def post(self)

# Initialises browser
        def init_browser():
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            # Suppress noisy Chrome logs
            options.add_experimental_option("excludeSwitches", ["enable-logging"])
            options.add_argument("--disable-logging")
            return webdriver.Chrome(options=options)
        
        # Closes RockAuto popup
        def close_popup(driver):
            try:
                print("→ Checking for popup...")
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'img[alt="Close"]'))
                )
                close_button = driver.find_element(By.CSS_SELECTOR, 'img[alt="Close"]')
                close_button.click()
                print("→ Popup closed.")
                time.sleep(1)
            except:
                print("→ No popup found.")

        # Inputs the YMM into the search ar
        def perform_top_search(driver, search_term):
            try:
                # Use RockAuto's main search box selector
                search_box = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[placeholder*="year make model"]'))
                )
                search_box.clear()
                search_box.send_keys(search_term)
                time.sleep(0.5)
                search_box.send_keys(Keys.ENTER)
                print(f"→ Performed top search for: {search_term}")
                # Let results load
                time.sleep(3)
            except Exception as e:
                print(f"[!] Top search failed ({type(e).__name__}): {e}")

        #Finds oil filter brands by elemetn and then also scrapes part number
        def scrape_oil_filters(driver, brand_filter=None):
            try:
                # Wait for filter part numbers and manufacturers
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.listing-final-partnumber.as-link-if-js'))
                )
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'span.listing-final-manufacturer'))
                )
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                results = []
        
                brands = soup.select('span.listing-final-manufacturer')
                parts = soup.select('span.listing-final-partnumber.as-link-if-js')
                if not brands or not parts:
                    print("[!] No filter elements found on page.")
                    return []
                if len(brands) != len(parts):
                    print(f"[!] Warning: found {len(brands)} brands but {len(parts)} parts; pairing by index.")
        
                for brand_tag, part_tag in zip(brands, parts):
                    brand = brand_tag.get_text(strip=True)
                    part  = part_tag.get_text(strip=True)
                    if brand_filter and not any(b.lower() in brand.lower() for b in brand_filter):
                        continue
                    results.append(f"{brand}: {part}")
        
                return results

            except Exception as e:
                print(f"[!] Oil filter scraping failed ({type(e).__name__}): {e}")
                return []

# Finds oil types and strips for viscosity
        def scrape_oil_types(driver):
            try:
                # Wait for oil type spans
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'span.span-link-underline-remover'))
                )
                time.sleep(1)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                viscosities = []
                for span in soup.select('span.span-link-underline-remover'):
                    text = span.get_text(strip=True)
                    # Extract viscosity pattern like '5W-30'
                    match = re.search(r"(\d+[wW]-\d+)", text)
                    if match:
                        viscosities.append(match.group(1).lower())
                # Remove duplicates
                seen = set()
                unique = []
                for v in viscosities:
                    if v not in seen:
                        seen.add(v)
                        unique.append(v)
                return unique
        
            except Exception as e:
                print(f"[!] Oil type scraping failed ({type(e).__name__}): {e}")
                return []
        
        
        def scrape_oil_info(driver, search_base, brand_filter=None):
            try:
                driver.get("https://www.rockauto.com/")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )
                time.sleep(2)
                close_popup(driver)
        
                perform_top_search(driver, f"{search_base} oil filter")
                oil_filters = scrape_oil_filters(driver, brand_filter)
        
                perform_top_search(driver, f"{search_base} oil")
                oil_types = scrape_oil_types(driver)
        
                oil_capacity_estimates = {
                    '1.4l l4': '4.0 quarts',
                    '1.8l l4': '4.4 quarts',
                    '2.0l l4': '4.7 quarts',
                    '2.4l l4': '5.5 quarts',
                    '5.0l v8': '7.7 quarts'
                }
                engine_key = ' '.join(search_base.lower().split()[-2:])
                if engine_key.endswith('4l'):
                    engine_key = engine_key.replace('4l', 'l4')
                oil_capacity = oil_capacity_estimates.get(engine_key, 'Unknown')
        
                return { 'oil_filters': oil_filters, 'oil_types': oil_types, 'oil_capacity': oil_capacity }
        
            except Exception as e:
                print(f"[!] Failed to scrape oil info ({type(e).__name__}): {e}")
                return { 'oil_filters': [], 'oil_types': [], 'oil_capacity': 'Unknown' }


        def main():
            print("Enter vehicle info (e.g. 2020 Toyota Corolla 1.8L L4). Type 'done' when finished.")
            brand_input = input("Brands to include (comma-separated) or Enter for all: ").strip()
            brand_filter = [b.strip() for b in brand_input.split(',')] if brand_input else None
        
            vehicles = []
            while True:
                line = input("Vehicle: ").strip()
                if line.lower() == 'done': break
                try:
                    year, make, model, *engine = line.split()
                    vehicles.append((year, make, model, ' '.join(engine)))
                except:
                    print("Invalid format. Use: Year Make Model Engine")
        
            driver = init_browser()
            results = []
            for y, mk, md, eng in vehicles:
                desc = f"{y} {mk} {md} {eng}"
                print(f"\n=== {desc} ===")
                data = scrape_oil_info(driver, desc, brand_filter)
                print("Oil Filters:")
                if data['oil_filters']:
                    for f in data['oil_filters']:
                        print(' -', f)
                else:
                    print(' (none found)')
                print("Oil Types:")
                if data['oil_types']:
                    for o in data['oil_types']:
                        print(' -', o)
                else:
                    print(' (none found)')
                print("Oil Capacity:", data['oil_capacity'])
                results.append({
                    'Year': y, 'Make': mk, 'Model': md, 'Engine': eng,
                    'Oil Filters': '; '.join(data['oil_filters']),
                    'Oil Types': '; '.join(data['oil_types']),
                    'Oil Capacity': data['oil_capacity']
                })
        
            driver.quit()
            if results:
                mode = 'a' if os.path.isfile('results.csv') else 'w'
                with open('results.csv', mode, newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=results[0].keys())
                    if mode=='w': writer.writeheader()
                    writer.writerows(results)
                print("\n Results saved to results.csv")
            else:
                print("\n No results to save.")
        
        if __name__=='__main__':
            main()


# adding the defined resources along with their corresponding urls
api.add_resource(VINNum, '/VIN')
api.add_resource(Hello, '/')

api.add_resource(ImageOCR, '/ReadInfo')


# driver function
if __name__ == '__main__':
   app.run(host='0.0.0.0', port=5000, debug=True)
