import base64
import openai

from dotenv import load_dotenv
import os

#loading env file with API key
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

openai.api_key = api_key

# Initialize client (make sure OPENAI_API_KEY is in your environment variables)
client = openai.OpenAI()

# Path to your test image
image_path = "./uploads/full.jpeg"

# Read and encode image to base64
with open(image_path, "rb") as f:
    image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

# Define the request
prompt = """
You are an OCR and document parsing assistant.
From this repair order image, extract ONLY the following in JSON format:
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
print(response.choices[0].message.content)
