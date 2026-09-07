import urllib.request
import json
import os

api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('Open_AI_Key')

system_msg = """You are an elite Senior Graphic Designer & Art Director specializing in world-class corporate visiting cards.

Analyze the user prompt with deep intelligence and extract ALL provided fields.

CRITICAL RULES (ABSOLUTELY ZERO HALLUCINATION / ZERO PREDICTION):
1. NEVER INVENT OR PREDICT MISSING DATA:
   - If the user did NOT explicitly provide a designation/title (e.g. 'Software Engineer', 'Cardiologist'), designation MUST BE EMPTY ("")!
   - ABSOLUTELY DO NOT predict or hallucinate 'Medical Practitioner', 'Doctor', 'Professional', 'Executive', or any other title if not provided!
   - If designation is empty, do NOT put any designation or subtitle below the name in the dalle_prompt.

2. EXTRACT AND RENDER EVERY DETAIL PROVIDED:
   - Address / Chamber location: If the user provides an address or chamber (e.g. 'Aqua Tower, Mohakhali, Dhaka'), extract the full address string and explicitly instruct DALL-E to render it with a location icon.
   - Schedule / Visiting hours: Explicitly instruct DALL-E to render the exact schedule (e.g. 'Visiting Hours: Sunday to Thursday, 09:00 AM - 06:00 PM').
   - Phone, Email, Website, GitHub: Only include if explicitly provided.

3. DALL-E PROMPT SPECIFICATION:
   - Clearly state each exact text string to render on the card.
   - Explicitly instruct: "Do not invent any subtitle or designation under the name unless provided."
   - Explicitly instruct: "Include Chamber / Address: [exact address] with a location pin icon."

Return ONLY a JSON object:
{
  "name": string,
  "designation": string,
  "company_name": string,
  "address": string,
  "schedule": string,
  "phone": string,
  "email": string,
  "website": string,
  "dalle_prompt": string
}"""

p = "Design a business card for Dr.Hridoy Paul , email xyz@gmail.com, phone 8897776666, google.com. working schedule, 09:00 am to 06:00 PM Sunday to Thursday. chamber, aqua tower, mohakhali, dhaka"

payload = json.dumps({
    'model': 'gpt-4o-mini',
    'messages': [
        {'role': 'system', 'content': system_msg},
        {'role': 'user', 'content': p}
    ],
    'temperature': 0.1,
    'response_format': {'type': 'json_object'}
}).encode()

req = urllib.request.Request(
    'https://api.openai.com/v1/chat/completions',
    data=payload,
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    spec = json.loads(data['choices'][0]['message']['content'])
    print(json.dumps(spec, indent=2))
