import io
import json
import logging
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from PIL import Image

from .models import CardSession, CardMessage, GeneratedCard
from .serializers import (
    CardSessionSerializer,
    CardMessageSerializer,
    CardChatSerializer,
    CardPromptSerializer,
)
from .services.gemini_service import (
    generate_business_card_with_ai,
    get_active_ai_config,
    save_ai_config,
    is_new_card_intent,
)
from .services.card_templates import render_fallback_card
from .services.image_renderer import render_business_card_image

logger = logging.getLogger(__name__)



class HealthCheckView(APIView):
    """
    Health check endpoint for Docker container orchestration.
    GET /api/health/
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            "status": "healthy",
            "service": "AI Visiting Card Generator & Agentic Chat Studio",
            "framework": "Django REST Framework",
            "capabilities": [
                "Single-Shot visiting card generation via POST /api/generate-card/",
                "Multi-Turn Agentic Chat Design via POST /api/generate-card/",
                "Session history & version tracking via GET /api/generate-card/<session_id>/"
            ],
            "endpoints": {
                "chat_agent": "POST /api/generate-card/ with {\"session_id\": \"optional\", \"message\": \"...\"}",
                "single_shot": "POST /api/generate-card/ with {\"prompt\": \"...\"}",
                "health": "GET /api/health/"
            }
        }, status=200)


class OpenAIKeyConfigAPIView(APIView):
    """
    Secure management endpoint for AI API Key.
    GET /api/config/openai-key/
    POST /api/config/openai-key/
    PUT /api/config/openai-key/
    DELETE /api/config/openai-key/
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        ai_config = get_active_ai_config()
        raw_key = ai_config.get("api_key", "")
        masked_key = ""
        if raw_key:
            if len(raw_key) > 8:
                masked_key = f"{raw_key[:4]}...{raw_key[-4:]}"
            else:
                masked_key = "********"

        return Response({
            "success": True,
            "is_configured": bool(raw_key),
            "provider": ai_config.get("provider", "gemini"),
            "project_id": ai_config.get("project_id", ""),
            "masked_key": masked_key,
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self._save_key(request)

    def put(self, request, *args, **kwargs):
        return self._save_key(request)

    def _save_key(self, request):
        api_key = (
            request.data.get('api_key') or
            request.data.get('openai_key') or
            request.data.get('openai_api_key') or
            request.data.get('gemini_key') or
            ""
        ).strip()

        provider = request.data.get('provider')
        project_id = request.data.get('project_id', '').strip()

        if not api_key:
            return Response({
                "success": False,
                "error": "The 'api_key' field is required and cannot be empty."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not provider:
            provider = "openai" if api_key.startswith("sk-") else "gemini"

        saved = save_ai_config(api_key, provider, project_id=project_id)
        masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "********"

        return Response({
            "success": True,
            "message": "AI API key saved successfully.",
            "masked_key": masked_key,
            "provider": saved.get("provider", "gemini"),
            "project_id": saved.get("project_id", ""),
            "is_configured": True
        }, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        save_ai_config("", provider="gemini", project_id="")
        return Response({
            "success": True,
            "message": "Database OpenAI key cleared. System reverted to environment default.",
            "is_configured": False
        }, status=status.HTTP_200_OK)



class CardChatAPIView(APIView):
    """
    Conversational AI Visiting Card Studio endpoint.
    Supports multi-turn iterative design (like ChatGPT / Gemini).

    POST /api/generate-card/
    Body:
      {
        "session_id": "optional-uuid",
        "message": "Create a modern visiting card for my name : mamun"
      }

    Response:
      {
        "status": "success",
        "session_id": "...",
        "version": 1,
        "assistant_message": "I've created your visiting card...",
        "card_data": { ... },
        "image_base64": "data:image/png;base64,...",
        "image_url": "data:image/png;base64,...",
      }
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        prompt = request.query_params.get('message') or request.query_params.get('prompt')
        if prompt:
            return self._handle_card_turn(request, prompt=prompt, session_id_str=None)
        
        sessions = CardSession.objects.all().order_by('-updated_at')[:20]
        serializer = CardSessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        prompt = ""
        session_id_str = None

        if hasattr(request, 'data') and request.data:
            nested_data = request.data.get('data')
            if isinstance(nested_data, dict):
                prompt = (
                    nested_data.get('massage') or
                    nested_data.get('message') or
                    nested_data.get('prompt') or
                    ""
                )
                session_id_str = nested_data.get('session_id')
            elif isinstance(nested_data, str):
                try:
                    parsed = json.loads(nested_data)
                    if isinstance(parsed, dict):
                        prompt = (
                            parsed.get('massage') or
                            parsed.get('message') or
                            parsed.get('prompt') or
                            ""
                        )
                        session_id_str = parsed.get('session_id')
                except Exception:
                    pass

            if not prompt:
                prompt = (
                    request.data.get('massage') or
                    request.data.get('message') or
                    request.data.get('prompt') or
                    ""
                )
            if not session_id_str:
                session_id_str = request.data.get('session_id')

        if not prompt and request.body:
            try:
                b_data = json.loads(request.body.decode('utf-8'))
                nested_data = b_data.get('data')
                if isinstance(nested_data, dict):
                    prompt = (
                        nested_data.get('massage') or
                        nested_data.get('message') or
                        nested_data.get('prompt') or
                        ""
                    )
                    session_id_str = session_id_str or nested_data.get('session_id')
                elif isinstance(nested_data, str):
                    try:
                        parsed = json.loads(nested_data)
                        if isinstance(parsed, dict):
                            prompt = (
                                parsed.get('massage') or
                                parsed.get('message') or
                                parsed.get('prompt') or
                                ""
                            )
                            session_id_str = session_id_str or parsed.get('session_id')
                    except Exception:
                        pass

                if not prompt:
                    prompt = (
                        b_data.get('massage') or
                        b_data.get('message') or
                        b_data.get('prompt') or
                        ""
                    )
                if not session_id_str:
                    session_id_str = session_id_str or b_data.get('session_id')
            except Exception:
                pass

        if not prompt:
            prompt = (
                request.POST.get('massage') or
                request.POST.get('message') or
                request.POST.get('prompt') or
                ""
            )
            session_id_str = session_id_str or request.POST.get('session_id')

        prompt = str(prompt).strip()

        # 1. Check multipart/form-data files under all common key names
        reference_image_file = None
        if hasattr(request, 'FILES') and request.FILES:
            reference_image_file = (
                request.FILES.get('reference_image') or
                request.FILES.get('image') or
                request.FILES.get('file') or
                request.FILES.get('card_image') or
                request.FILES.get('photo') or
                next(iter(request.FILES.values()), None)
            )

        # 2. Check JSON data for Base64 image (either inside 'data' or at root)
        if not reference_image_file:
            raw_b64 = None
            if hasattr(request, 'data') and request.data:
                nested = request.data.get('data')
                if isinstance(nested, dict):
                    raw_b64 = (
                        nested.get('reference_image') or
                        nested.get('image') or
                        nested.get('card_image') or
                        nested.get('file')
                    )
                if not raw_b64:
                    raw_b64 = (
                        request.data.get('reference_image') or
                        request.data.get('image') or
                        request.data.get('card_image') or
                        request.data.get('file')
                    )

            if not raw_b64 and request.body:
                try:
                    b_data = json.loads(request.body.decode('utf-8'))
                    nested = b_data.get('data')
                    if isinstance(nested, dict):
                        raw_b64 = (
                            nested.get('reference_image') or
                            nested.get('image') or
                            nested.get('card_image') or
                            nested.get('file')
                        )
                    if not raw_b64:
                        raw_b64 = (
                            b_data.get('reference_image') or
                            b_data.get('image') or
                            b_data.get('card_image') or
                            b_data.get('file')
                        )
                except Exception:
                    pass

            if raw_b64 and isinstance(raw_b64, str):
                raw_b64 = raw_b64.strip()
                if raw_b64.startswith('data:image') or len(raw_b64) > 100:
                    try:
                        import base64
                        if ',' in raw_b64:
                            raw_b64 = raw_b64.split(',', 1)[1]
                        img_bytes = base64.b64decode(raw_b64)
                        reference_image_file = io.BytesIO(img_bytes)
                    except Exception as e:
                        logger.warning(f"Could not parse base64 reference image: {e}")

        if not prompt and not reference_image_file:
            return Response(
                {"status": "error", "error": "Please provide 'message' or a reference image."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return self._handle_card_turn(
            request,
            prompt=prompt,
            session_id_str=session_id_str,
            reference_image_file=reference_image_file
        )

    def _handle_card_turn(self, request, prompt, session_id_str=None, reference_image_file=None):
        # Retrieve or initialize session
        session = None
        if session_id_str:
            try:
                session = CardSession.objects.filter(id=session_id_str).first()
            except Exception:
                session = None

        is_new = is_new_card_intent(prompt)
        if not session or is_new:
            session = CardSession.objects.create(title="Corporate Business Card", version=1)
        else:
            session.version = (session.version or 1) + 1

        # Process reference image PURELY IN-MEMORY (NEVER SAVE TO DISK)
        in_memory_image = None
        if reference_image_file:
            try:
                reference_image_file.seek(0)
                in_memory_image = Image.open(reference_image_file)
            except Exception as e:
                logger.warning(f"Could not open in-memory reference image: {e}")

        # Save user message without saving any image to disk
        CardMessage.objects.create(
            session=session,
            sender='user',
            message=prompt,
            reference_image="",  # NO DISK IMAGE STORAGE
            version=session.version
        )

        # Contextual previous card state (if redesign iteration)
        previous_card = None
        if session.front_html and not is_new:
            previous_card = {
                "front_html": session.front_html,
                "back_html": session.back_html,
                "css": session.css,
                "card_data": session.card_data,
            }

        # Generate or redesign using AI (in-memory execution)
        try:
            ai_result = generate_business_card_with_ai(
                user_prompt=prompt,
                image_path=in_memory_image,
                previous_card=previous_card
            )
        except Exception as e:
            logger.error(f"Card generation failed: {e}")
            return Response({"status": "error", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        front_html = ai_result.get("front_html", "")
        back_html = ai_result.get("back_html", "")
        css = ai_result.get("css", "")
        raw_card_data = ai_result.get("card_data", {})
        bot_reply = ai_result.get("bot_reply", "I've created your visiting card design with front and back views.")
        title = ai_result.get("title")

        # Standardize card_data keys according to agent.md
        card_data = {
            "name": str(raw_card_data.get('name') or ''),
            "designation": str(raw_card_data.get('designation') or raw_card_data.get('title') or ''),
            "company_name": str(raw_card_data.get('company_name') or raw_card_data.get('company') or ''),
            "phone": str(raw_card_data.get('phone') or ''),
            "email": str(raw_card_data.get('email') or ''),
            "website": str(raw_card_data.get('website') or ''),
            "address": str(raw_card_data.get('address') or ''),
            "tagline": str(raw_card_data.get('tagline') or ''),
            "primary_color": str(raw_card_data.get('primary_color') or '#090d16'),
            "accent_color": str(raw_card_data.get('accent_color') or '#d4af37')
        }

        # Render high-resolution PNG & base64 image PURELY IN-MEMORY (NEVER SAVE TO DISK)
        try:
            png_bytes, b64_str = render_business_card_image(card_data)
        except Exception as e:
            logger.warning(f"Image rendering fallback error: {e}")
            png_bytes, b64_str = b"", ""

        # Update Session with active card state (no disk files)
        if title:
            session.title = title
        session.front_html = front_html
        session.back_html = back_html
        session.css = css
        session.card_data = card_data
        session.image_base64 = b64_str
        session.image_url = b64_str
        session.save()

        # Save Assistant response message
        CardMessage.objects.create(
            session=session,
            sender='assistant',
            message=bot_reply,
            front_html=front_html,
            back_html=back_html,
            css=css,
            card_data=card_data,
            image_base64=b64_str,
            image_url=b64_str,
            version=session.version
        )

        data_payload = {
            "massage": prompt,
            "message": prompt,
            "session_id": str(session.id),
            "version": session.version,
            "card_data": card_data,
            "image_base64": b64_str,
            "image_url": b64_str,
            "reference_image": b64_str,
            "card": {
                "front_html": front_html,
                "back_html": back_html,
                "css": css,
                "card_data": card_data,
            },
            "title": title or f"{card_data.get('name', 'Card')}",
            "assistant_message": bot_reply,
            "bot_reply": bot_reply
        }

        # Response schema matching generator response format with backward compatibility for web frontend UI
        return Response({
            "status": "success",
            "success": True,
            "session_id": str(session.id),
            "data": data_payload,
            "version": session.version,
            "assistant_message": bot_reply,
            "bot_reply": bot_reply,
            "card_data": card_data,
            "image_base64": b64_str,
            "image_url": b64_str,
            "reference_image": b64_str,
            "user_prompt": prompt,
            "note": "AI-generated cards should be manually verified for text accuracy before printing or sharing.",
            "card": {
                "front_html": front_html,
                "back_html": back_html,
                "css": css,
                "card_data": card_data,
            },
            "title": title or f"{card_data.get('name', 'Card')}"
        }, status=status.HTTP_200_OK)



class CardSessionHistoryAPIView(APIView):
    """
    Retrieves full message history and past versions of a design session.
    GET /api/generate-card/<uuid:session_id>/
    POST /api/generate-card/<uuid:session_id>/ (for redesign)
    """
    permission_classes = [AllowAny]

    def get(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(CardSession, id=session_id)
        
        messages_data = []
        for m in session.messages.all().order_by('created_at'):
            messages_data.append({
                "role": m.sender,
                "content": m.message,
                "card_data": m.card_data,
                "image_base64": m.image_base64 or m.image_url,
                "image_url": m.image_base64 or m.image_url,
                "version": m.version,
                "created_at": m.created_at.isoformat()
            })

        data_payload = {
            "session_id": str(session.id),
            "current_version": session.version,
            "current_state": session.card_data,
            "card_data": session.card_data,
            "messages": messages_data,
        }

        # EXACT response schema matching agent.md lines 101-109 (NO EXTRA KEYS)
        return Response({
            "session_id": str(session.id),
            "data": data_payload,
            "current_version": session.version,
            "current_state": session.card_data,
            "card_data": session.card_data,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": messages_data
        }, status=status.HTTP_200_OK)

    def post(self, request, session_id, *args, **kwargs):
        chat_view = CardChatAPIView()
        prompt = ""
        if hasattr(request, 'data') and request.data:
            nested_data = request.data.get('data')
            if isinstance(nested_data, dict):
                prompt = (
                    nested_data.get('massage') or
                    nested_data.get('message') or
                    nested_data.get('prompt') or
                    ""
                )
            elif isinstance(nested_data, str):
                try:
                    parsed = json.loads(nested_data)
                    if isinstance(parsed, dict):
                        prompt = (
                            parsed.get('massage') or
                            parsed.get('message') or
                            parsed.get('prompt') or
                            ""
                        )
                except Exception:
                    pass

            if not prompt:
                prompt = (
                    request.data.get('massage') or
                    request.data.get('message') or
                    request.data.get('prompt') or
                    ""
                )

        if not prompt and request.POST:
            prompt = (
                request.POST.get('massage') or
                request.POST.get('message') or
                request.POST.get('prompt') or
                ""
            )
            
        reference_image_file = None
        if hasattr(request, 'FILES') and request.FILES:
            reference_image_file = (
                request.FILES.get('reference_image') or
                request.FILES.get('image') or
                request.FILES.get('file') or
                request.FILES.get('card_image') or
                request.FILES.get('photo') or
                next(iter(request.FILES.values()), None)
            )

        if not reference_image_file:
            raw_b64 = None
            if hasattr(request, 'data') and request.data:
                nested = request.data.get('data')
                if isinstance(nested, dict):
                    raw_b64 = (
                        nested.get('reference_image') or
                        nested.get('image') or
                        nested.get('card_image') or
                        nested.get('file')
                    )
                if not raw_b64:
                    raw_b64 = (
                        request.data.get('reference_image') or
                        request.data.get('image') or
                        request.data.get('card_image') or
                        request.data.get('file')
                    )

            if not raw_b64 and request.body:
                try:
                    b_data = json.loads(request.body.decode('utf-8'))
                    nested = b_data.get('data')
                    if isinstance(nested, dict):
                        raw_b64 = (
                            nested.get('reference_image') or
                            nested.get('image') or
                            nested.get('card_image') or
                            nested.get('file')
                        )
                    if not raw_b64:
                        raw_b64 = (
                            b_data.get('reference_image') or
                            b_data.get('image') or
                            b_data.get('card_image') or
                            b_data.get('file')
                        )
                except Exception:
                    pass

            if raw_b64 and isinstance(raw_b64, str):
                raw_b64 = raw_b64.strip()
                if raw_b64.startswith('data:image') or len(raw_b64) > 100:
                    try:
                        import base64
                        if ',' in raw_b64:
                            raw_b64 = raw_b64.split(',', 1)[1]
                        img_bytes = base64.b64decode(raw_b64)
                        reference_image_file = io.BytesIO(img_bytes)
                    except Exception as e:
                        logger.warning(f"Could not parse base64 reference image: {e}")

        return chat_view._handle_card_turn(
            request,
            prompt=str(prompt).strip(),
            session_id_str=str(session_id),
            reference_image_file=reference_image_file
        )
