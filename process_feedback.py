import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ISSUE_BODY = os.environ.get('ISSUE_BODY', '')

if not ISSUE_BODY:
    print("No issue body found. Exiting.")
    exit()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

prompt = f"""
Read the following paper abstract. Extract 1 to 3 broad, single-word or two-word scientific keywords related to environmental microbiology.
Return ONLY the keywords, separated by commas, all lowercase. Do not include introductory text.
Abstract: {ISSUE_BODY}
"""
try:
    response = model.generate_content(prompt)
    new_keywords = [k.strip() for k in response.text.split(',') if k.strip()]
    
    # Append the new keywords to the library
    with open('keywords.txt', 'a') as f:
        for kw in new_keywords:
            f.write(f"\n{kw}")
            
    print(f"Successfully added keywords: {new_keywords}")
except Exception as e:
    print(f"Failed to extract keywords: {e}")