import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

user_prompt = input("Enter your prompt: ")

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=user_prompt
)

print("\nAI Response:")
print(response.text)
