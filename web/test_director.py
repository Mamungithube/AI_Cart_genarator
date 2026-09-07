import os
import json
import urllib.request

api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('Open_AI_Key')

system_prompt = """You are an elite AI Art Director & Visiting Card Architect.
You must think deeply like ChatGPT and generate a 100% customized, unique, professional prompt for gpt-image-1.

RULES FOR YOUR REASONING:
1. CARD FORMAT - ZERO OUTER BACKGROUND / FULL BLEED:
   - The card must fill the ENTIRE rectangular canvas edge-to-edge (full bleed).
   - Absolutely NO desk, NO table, NO outer backdrop, NO drop shadows outside the card, NO frame margins.
   - The entire 1536x1024 rectangular image IS the visiting card surface.

2. LOGO MUST BE ROOTED IN THE ENTITY / NAME:
   - The logo must be an emblem or crest created directly from the organization name or person name (e.g. For 'Bangladesh University' -> a prestigious university crest seal with the monogram initials 'BU'). Never use generic unrelated shapes.

3. PROFESSION-SPECIFIC AESTHETIC (NEVER REPETITIVE):
   - Academic / Teacher / Professor: Dignified, scholarly, prestigious university seal crest, elegant typography, refined educational accents (e.g. subtle book or quill watermark, laurel). ABSOLUTELY NO tech circuits or computer chips!
   - Software / Tech: Cybernetic, circuit traces, glowing nodes, modern tech emblem.
   - Doctor / Health: Clean, medical cross/caduceus, pristine minimalist layout.
   - Legal / Lawyer: Scales of justice, classical serif typography, authoritative layout.
   - Corporate / Business: Clean geometric luxury, brushed metallic badge.
   Every card MUST look completely different and tailored to the person's exact profession!

4. COLOR SCHEME - STRICTLY APPLY USER'S REQUESTED COLORS:
   - If user asks for 'white and green theme, make sure theme is gradient':
     The card surface background MUST be a smooth, luxurious gradient from crisp white to deep emerald/forest green!
     The text and icons must use high-contrast dark green or gold tones to be perfectly legible.

5. CONTENT & CONTACT:
   - Include Name ('Nahid'), Designation ('Teacher / Faculty'), Institution ('Bangladesh University').
   - Include clean contact details (phone, email, website) with matching minimalist icons.

Return ONLY a valid JSON object with keys:
name, designation, company_name, phone, email, website, linkedin, dalle_prompt
"""

user_input = 'i am a teacher , so create a visiting card with white and green theme. make sure theme is gradiun. also university name Bangladesh university.MY name is Nahid.'

payload = json.dumps({
    'model': 'gpt-4o-mini',
    'messages': [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_input}
    ],
    'temperature': 0.3,
    'response_format': {'type': 'json_object'}
}).encode()

req = urllib.request.Request(
    'https://api.openai.com/v1/chat/completions',
    data=payload,
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
)

with urllib.request.urlopen(req, timeout=30) as res:
    result = json.loads(res.read())
    parsed = json.loads(result['choices'][0]['message']['content'])
    print('Parsed data:')
    print(json.dumps(parsed, indent=2))
