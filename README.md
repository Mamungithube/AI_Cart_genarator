# Enterprise AI Visiting Card & Image Processing Microservice

A production-grade microservice built with **Django REST Framework (DRF)**, **PostgreSQL 16**, **Gunicorn**, **Nginx Reverse Proxy**, **rembg / OpenCV**, **Google Cloud Vision API**, and **OpenAI GPT-4o**.

The system provides two dedicated capabilities:
1. **AI Card Generation & Conversational Studio (`generator`)**: Multi-turn conversational design studio and prompt-based high-resolution visiting card generation.
2. **Card Scanning & Image Processing (`image_processor`)**: Background removal, 4-corner perspective cropping, orientation correction, image enhancement, and multi-modal structured data extraction.

---

## 🏛 Architecture & Project Structure

```
.
├── .dockerignore
├── .env                          # Environment variables & secrets (not committed to VCS)
├── .env.example                  # Template configuration file
├── .gitignore                    # Git ignore specifications
├── README.md                     # Project documentation
├── docker-compose.yml            # Multi-container orchestration (web, db, nginx)
├── nginx/
│   ├── Dockerfile                # Nginx Alpine container definition
│   └── default.conf              # Reverse proxy configuration with dual port (80, 6000) & CORS
├── samples/
│   └── sample_card.png           # Sample card image for verification and testing
└── web/
    ├── Dockerfile                # Python 3.11-slim container definition
    ├── entrypoint.sh             # Startup migration and service launch script
    ├── manage.py                 # Django management interface
    ├── requirements.txt          # Python production dependencies
    ├── card_project/             # Django root project configuration
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── settings.py           # Core settings, database, security, and installed apps
    │   ├── urls.py               # Root URL router
    │   └── wsgi.py               # WSGI entrypoint for Gunicorn
    ├── generator/                # App: AI Visiting Card Studio & Vector Generation
    │   ├── admin.py              # Django admin registrations
    │   ├── apps.py               # GeneratorConfig
    │   ├── models.py             # GeneratedCard, CardSession, CardMessage
    │   ├── serializers.py        # Serializers for prompt and chat payloads
    │   ├── urls.py               # /api/chat-card/, /api/generate-card/, /api/health/
    │   ├── views.py              # API views
    │   ├── tests.py              # Automated test suite
    │   ├── fonts/                # Bundled typography (bold.ttf, regular.ttf)
    │   ├── migrations/           # Database schema migrations
    │   └── services/
    │       ├── ai_card_drawer.py # OpenAI DALL-E & hybrid card layout engine
    │       ├── card_agent.py     # Multi-turn conversational card architect
    │       └── card_drawer.py    # High-DPI vector card rendering & styles
    └── image_processor/          # App: Card Detection, Cropping & OCR Extraction
        ├── apps.py               # ImageProcessorConfig
        ├── urls.py               # /process-card, /api/process-card/, /enhance-card, /api/enhance-card/
        ├── views.py              # ProcessCardView, EnhanceCardView
        ├── tests.py              # Automated test suite
        └── services/
            ├── cropper.py        # rembg background removal & perspective warp
            ├── enhancer.py       # LAB CLAHE, bilateral filter, unsharp mask
            └── extractor.py      # Google Vision OCR, orientation rotation & GPT-4o extraction
```

---

## 🚀 Quick Start

### 1. Environment Setup
Copy the example environment file and set your credentials:
```bash
cp .env.example .env
```
Ensure the following variables are configured in `.env`:
```env
OPENAI_API_KEY=your_openai_api_key
GOOGLE_VISION_API_KEY=your_google_cloud_vision_key
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=*
```

### 2. Build & Launch Containers
```bash
docker compose up -d --build
```

### 3. Verify Container Status
```bash
docker compose ps
```
All three containers (`drf_card_db`, `drf_card_web`, `drf_card_nginx`) should report healthy status.

## 🔒 API Authentication & Security

All visiting card generation and image processing endpoints are protected by a fixed API Key (`API_SECRET_KEY`) to prevent unauthorized public access and prevent API bill abuse:

- **Configured in**: `.env` as `API_SECRET_KEY`
- **Supported Header**: `X-API-KEY: <your-key>` or `X-API-Key: <your-key>`
- **Supported Authorization**: `Authorization: Bearer <your-key>`
- **Supported Query Param**: `?api_key=<your-key>` (useful for GET image requests)
- **Public Exemptions**: `GET /api/health/` remains open for container orchestration health checks.

Requests without a valid key are immediately blocked with `401 Unauthorized` / `403 Forbidden`:
```json
{
  "success": false,
  "error": "Authentication failed: Missing API Key. Provide via 'X-API-KEY' header or 'Authorization: Bearer <key>'."
}
```

---

## 📡 API Endpoints

All protected endpoints require the `X-API-KEY` header.

### 1. Card Scanner & Data Extractor
* **Path**: `POST /process-card` or `POST /api/process-card/`
* **Ports**: Supported on both `http://localhost:6000` and `http://localhost:80`
* **Content-Type**: `multipart/form-data`
* **Parameters**:
  * `front`: (Optional file) Card front photo
  * `back`: (Optional file) Card back photo
  *(At least one image must be provided)*
* **Response**:
```json
{
  "success": true,
  "details": {
    "is_card": true,
    "card_type": "Business Card",
    "name": "Sarah Connor",
    "job_title": "Chief Technology Officer",
    "company": "Apex Innovations",
    "phones": ["+8801712345678"],
    "emails": ["sarah@apex.com"],
    "websites": [],
    "address": "",
    "social_media": {
      "facebook": [],
      "linkedin": [],
      "twitter": [],
      "instagram": [],
      "other": []
    },
    "other_details": ""
  },
  "front_image_base64": "<base64_jpeg>",
  "back_image_base64": null
}
```

### 2. Card Image Enhancer
* **Path**: `POST /enhance-card` or `POST /api/enhance-card/`
* **Ports**: `http://localhost:6000` and `http://localhost:80`
* **Content-Type**: `multipart/form-data`
* **Parameters**:
  * `image`: (Required file) Card image to enhance
* **Response**:
```json
{
  "success": true,
  "enhanced_image_base64": "<base64_jpeg>"
}
```

### 3. Conversational Visiting Card Studio (Multi-Turn)
* **Path**: `POST /api/chat-card/`
* **Content-Type**: `application/json`
* **Request**:
```json
{
  "session_id": "optional-uuid-v4",
  "message": "Create a luxury visiting card for John Doe, CEO of Acme Inc, with phone 01700000000"
}
```
* **Response**: Returns created `session_id`, version, generated image URL, and assistant response.

### 4. OpenAI Key Dynamic Configuration (AES-256 Encrypted in DB)
* **Path**: `GET` / `POST` / `DELETE` on `/api/config/openai-key/` or `/config/openai-key`
* **Ports**: `http://localhost:6000` and `http://localhost:80`
* **Headers**: `X-API-KEY: <your-api-secret-key>`
* **Features**:
  - Dynamically rotate/change OpenAI API key via API without touching `.env` or restarting containers.
  - Automatically encrypted with AES-256 (Fernet) in PostgreSQL with SHA-256 fingerprint.
  - **GET**: Inspect active key source (`database` or `environment`), configuration status, and safe masked preview (e.g. `sk-proj...3210`).
  - **POST / PUT**: Set new OpenAI key:
    ```json
    {
      "api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxx",
      "validate": true
    }
    ```
  - **DELETE**: Remove custom key from database and revert automatically to `.env` fallback.

### 5. Health Check
* **Path**: `GET /api/health/`
* **Response**:
```json
{
  "status": "healthy",
  "service": "drf-business-card-generator",
  "framework": "Django REST Framework"
}
```

---

## 🧪 Running Automated Tests

Run the full Django test suite inside Docker:
```bash
docker compose exec web python manage.py test
```
All tests for both `generator` and `image_processor` run in an isolated test database.