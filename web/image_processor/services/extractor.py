import base64
import json
import cv2
import requests

FINANCIAL_CARD_TYPES = {"Credit Card", "Debit Card", "ATM Card", "Gift Card"}

BUSINESS_TYPES = [
    'Accountant', 'App Developer', 'Auto Parts', 'Barber', 'Cafe', 'Car Rental',
    'Carpenter', 'Catering', 'Cleaner', 'Clothing Store', 'Coaching Center',
    'Construction', 'Courier Service', 'Dentist', 'Digital Marketer', 'Doctor',
    'Electrician', 'Electronics Store', 'Grocery Store', 'Home Inspector',
    'Hospital', 'Insurance Agent', 'Lawyer', 'Loan Officer', 'Mechanic',
    'Painter', 'Pharmacy', 'Plumber', 'Property Dealer', 'Realtor',
    'Restaurant', 'Salon', 'Software Company', 'Teacher', 'Travel Agent'
]

PERSONAL_TYPES = [
    "ATM Card", "Boarding Pass", "Business Card", "Credit Card", "Debit Card",
    "Driving License", "Employee ID", "Gift Card", "Gym Card", "Library Card",
    "Loyalty Card", "Membership Card", "National ID", "Passport", "Personal Card",
    "Student ID", "Transport Card", "Travel Card", "Visiting Card"
]


def _mask_card_number(number: str) -> str:
    digits = number.replace(" ", "").replace("-", "")
    if len(digits) >= 4:
        return f"****  ****  ****  {digits[-4:]}"
    return "****  ****  ****  ****"


def _extract_text_with_vision(image_b64: str, vision_api_key: str) -> str:
    if not vision_api_key:
        return ""
    url = f"https://vision.googleapis.com/v1/images:annotate?key={vision_api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION"}]
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, timeout=25)
        data = response.json()
        return data["responses"][0]["fullTextAnnotation"]["text"].strip()
    except Exception:
        return ""


def _detect_rotation_with_vision(image_b64: str, vision_api_key: str) -> int:
    if not vision_api_key:
        return 0
    url = f"https://vision.googleapis.com/v1/images:annotate?key={vision_api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION"}],
                "imageContext": {"languageHints": ["en"]}
            }
        ]
    }
    try:
        response = requests.post(url, json=payload, timeout=25)
        data = response.json()
        pages = data["responses"][0]["fullTextAnnotation"]["pages"]
        blocks = pages[0]["blocks"]
        if not blocks:
            return 0

        vertices = blocks[0]["boundingBox"]["vertices"]
        v0, v1, v3 = vertices[0], vertices[1], vertices[3]
        x0, y0 = v0.get("x", 0), v0.get("y", 0)
        x1, y1 = v1.get("x", 0), v1.get("y", 0)
        x3, y3 = v3.get("x", 0), v3.get("y", 0)

        if x1 >= x0 and y3 >= y0:
            return 0
        elif x1 <= x0 and y3 >= y0:
            return 90
        elif x1 <= x0 and y3 <= y0:
            return 180
        else:
            return 270
    except Exception:
        return 0


def _detect_rotation_and_extract_text(image_b64: str, vision_api_key: str):
    if not vision_api_key:
        return 0, ""

    url = f"https://vision.googleapis.com/v1/images:annotate?key={vision_api_key}"
    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION"}],
                "imageContext": {"languageHints": ["en"]}
            }
        ]
    }
    rotation = 0
    raw_text = ""

    try:
        response = requests.post(url, json=payload, timeout=25)
        data = response.json()
        pages = data["responses"][0]["fullTextAnnotation"]["pages"]
        blocks = pages[0]["blocks"]

        if blocks:
            vertices = blocks[0]["boundingBox"]["vertices"]
            v0, v1, v3 = vertices[0], vertices[1], vertices[3]
            x0, y0 = v0.get("x", 0), v0.get("y", 0)
            x1, y1 = v1.get("x", 0), v1.get("y", 0)
            x3, y3 = v3.get("x", 0), v3.get("y", 0)

            if x1 >= x0 and y3 >= y0:
                rotation = 0
            elif x1 <= x0 and y3 >= y0:
                rotation = 90
            elif x1 <= x0 and y3 <= y0:
                rotation = 180
            else:
                rotation = 270

        raw_text = data["responses"][0]["fullTextAnnotation"]["text"].strip()
    except Exception:
        pass

    return rotation, raw_text


def _build_prompt(raw_text: str) -> str:
    return f"""
You are a card data extractor. Below is raw text extracted from a card image via OCR.
Your job is to parse it into structured JSON.
Only return is_card: false if the text is completely empty or pure gibberish with no meaningful words.
Otherwise always treat it as a card and extract whatever is visible.

RAW TEXT:
{raw_text}

Step 1: Is this text from a card?
If not, return only: {{"is_card": false}}

Step 2: Identify the card type.
Business types: {json.dumps(BUSINESS_TYPES)}
Personal types: {json.dumps(PERSONAL_TYPES)}
If none match, write your best short label.

Step 3: Extract visible data based on card type.

If card_type is one of: Credit Card, Debit Card, ATM Card, Gift Card:
{{
  "is_card": true,
  "card_type": "",
  "bank_name": "",
  "cardholder_name": "",
  "card_number": "****  ****  ****  XXXX",
  "expiry": "**/**",
  "cvv": "***"
}}

For all other card types:
{{
  "is_card": true,
  "card_type": "",
  "name": "",
  "job_title": "",
  "company": "",
  "phones": [],
  "emails": [],
  "websites": [],
  "address": "",
  "social_media": {{
    "facebook": [],
    "linkedin": [],
    "twitter": [],
    "instagram": [],
    "other": []
  }},
  "other_details": ""
}}

Rules:
- Only use data from the raw text above
- Never hallucinate or guess
- Multiple values go in arrays
- Return JSON only, no explanation, no markdown
"""


def extract_with_rotation(front_bgr, back_bgr, openai_api_key: str, vision_api_key: str):
    """
    Rotates front & back correctly, sends OCR text to GPT-4o, and extracts structured data.
    """
    rotated_front = front_bgr
    raw_text = ""

    if front_bgr is not None:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        success, buffer = cv2.imencode(".jpg", front_bgr, encode_params)
        image_b64 = base64.b64encode(buffer).decode("utf-8")

        rotation = 0
        if vision_api_key:
            rotation, raw_text = _detect_rotation_and_extract_text(image_b64, vision_api_key)

        if rotation == 90:
            rotated_front = cv2.rotate(front_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rotation == 180:
            rotated_front = cv2.rotate(front_bgr, cv2.ROTATE_180)
        elif rotation == 270:
            rotated_front = cv2.rotate(front_bgr, cv2.ROTATE_90_CLOCKWISE)

    # Process back image rotation
    rotated_back = back_bgr
    if back_bgr is not None:
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]
        success, buffer = cv2.imencode(".jpg", back_bgr, encode_params)
        image_b64 = base64.b64encode(buffer).decode("utf-8")

        back_rotation = 0
        back_text = ""
        if vision_api_key:
            back_rotation, back_text = _detect_rotation_and_extract_text(image_b64, vision_api_key)

        if back_rotation == 90:
            rotated_back = cv2.rotate(back_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif back_rotation == 180:
            rotated_back = cv2.rotate(back_bgr, cv2.ROTATE_180)
        elif back_rotation == 270:
            rotated_back = cv2.rotate(back_bgr, cv2.ROTATE_90_CLOCKWISE)

        if back_text:
            raw_text = (raw_text + "\n---\n" + back_text).strip()

    # Send to GPT-4o
    if raw_text:
        payload = json.dumps({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": _build_prompt(raw_text)}],
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        req = requests.post(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            timeout=35
        )
        content = req.json()["choices"][0]["message"]["content"]
        clean = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean)
    else:
        # Direct OpenAI Vision fallback
        content = [
            {"type": "text", "text": _build_prompt("Card images uploaded")}
        ]
        if rotated_front is not None:
            _, fb = cv2.imencode(".jpg", rotated_front, [cv2.IMWRITE_JPEG_QUALITY, 85])
            fb_b64 = base64.b64encode(fb).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{fb_b64}"}
            })
        if rotated_back is not None:
            _, bb = cv2.imencode(".jpg", rotated_back, [cv2.IMWRITE_JPEG_QUALITY, 85])
            bb_b64 = base64.b64encode(bb).decode("utf-8")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{bb_b64}"}
            })

        payload = json.dumps({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 1000,
            "response_format": {"type": "json_object"}
        }).encode("utf-8")

        req = requests.post(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            },
            timeout=40
        )
        content = req.json()["choices"][0]["message"]["content"]
        result = json.loads(content)

    # Mask financial card numbers
    if result.get("card_type") in FINANCIAL_CARD_TYPES:
        result["card_number"] = _mask_card_number(result.get("card_number", ""))
        result["cvv"] = "***"
        result["expiry"] = "**/**"
        for field in ["name", "job_title", "company", "phones", "emails",
                      "websites", "address", "social_media", "other_details"]:
            result.pop(field, None)

    return rotated_front, rotated_back, result
