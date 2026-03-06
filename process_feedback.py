import os

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ISSUE_BODY = os.environ.get('ISSUE_BODY', '')

if not ISSUE_BODY:
    print("No issue body found. Exiting.")
    exit()

# Initialize the new Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = f"""
Read the following paper abstract. Extract 1 to 3 broad, single-word or two-word scientific keywords related to environmental microbiology.
Return ONLY the keywords, separated by commas, all lowercase. Do not include introductory text.
Abstract: {ISSUE_BODY}
"""

try:
    # Updated API call syntax using the new client
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    )
    
    # Clean up the response and split it into a list
    new_keywords = [k.strip() for k in response.text.split(',') if k.strip()]
    
    # Append the new keywords to the library file
    with open('keywords.txt', 'a') as f:
        for kw in new_keywords:
            f.write(f"\n{kw}")
            
    print(f"Successfully added keywords: {new_keywords}")
except Exception as e:
    print(f"Failed to extract keywords: {e}")

