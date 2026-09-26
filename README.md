# 🪪 AI Business Card Studio (Django + Gemini + Docker)

A modern, professional visiting card generator and iterative redesigner web application. It autonomously synthesizes executive business cards (Front & Back) from natural language prompts and reference images using Google Gemini Vision AI.

---

## 🚀 Live Access

> **Note on Browser Port Security:** Modern web browsers (Google Chrome, Mozilla Firefox) block port `6000` (X11 port) by default with `ERR_UNSAFE_PORT`. Therefore, external access is routed through port **`6001`** (and backend port `6000` remains active internally):

* **Web UI Dashboard:** **[http://localhost:6001](http://localhost:6001)**
* **Health Check API:** [http://localhost:6001/api/health/](http://localhost:6001/api/health/) (or `http://localhost:6000/api/health/`)
* **AI Key Config API:** [http://localhost:6001/api/config/openai-key/](http://localhost:6001/api/config/openai-key/)

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate-card/` | Generate a new business card (supports natural language prompt & optional reference image) |
| `GET` | `/api/generate-card/` | List recent card generation sessions |
| `POST` | `/api/generate-card/<uuid:session_id>/` | **Iterative Card Redesign** (Submit follow-up chat feedback for an existing card session) |
| `GET` | `/api/generate-card/<uuid:session_id>/` | Retrieve full chat history, versions, and current HTML/CSS card code |
| `POST` | `/api/extract/` | OCR & contact extraction from visiting card image via Gemini Vision (`X-API-Secret` required) |
| `GET` | `/api/health/` | Service health status and Docker container check |
| `GET/POST`| `/api/config/openai-key/` | Gemini / OpenAI API key configuration and validation |
| `GET/POST`| `/config/openai-key` | API key route alias |

---

## 🛠️ Key Features

1. **Free-Form Chatbot Prompting:**
   - No rigid or tedious forms. Type your name, title, company, phone, email, and design preferences in plain language in the chatbox, and the AI automatically parses every detail.
2. **Multimodal Reference Image Synthesis (Gemini Vision):**
   - Drop or upload any reference visiting card image. The AI analyzes its geometry, typography hierarchy, and color palette, replicating the aesthetic layout with clean, custom code.
   - **Smart QR Filtering:** Automatically ignores QR codes/barcodes from reference images, keeping cards clean and executive.
3. **Multi-Turn Iterative Redesign (Session ID):**
   - Refine existing designs seamlessly through chat feedback (e.g., *"Change primary color to navy blue"*, *"Make the font bolder"*, *"Align logo to the right"*). The AI preserves all user data across iterations.
4. **Print-Ready Professional Standards (Front & Back View):**
   - International standard size: `3.5" x 2"` (1.75:1 aspect ratio, 300 DPI print-ready canvas).
   - Interactive 3D flip animation for instant previewing.
   - One-click **High-Resolution PNG** and **Print-Ready PDF** downloads.
   - Clean, scoped HTML and modern CSS ready for copying.

---

## 🐳 Docker Commands

* **Start containers in background:**
  ```bash
  docker compose up -d
  ```
* **View live logs:**
  ```bash
  docker compose logs -f
  ```
* **Rebuild and restart after updates:**
  ```bash
  docker compose up -d --build web
  ```
* **Stop containers:**
  ```bash
  docker compose down
  ```
