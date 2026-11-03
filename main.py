import streamlit as st
import google.generativeai as genai
import os
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content("Say OK")
print(response.text)