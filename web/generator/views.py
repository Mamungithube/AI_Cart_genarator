import io
import json
import logging
import urllib.parse
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from card_project.permissions import HasAPIKey
from .serializers import CardPromptSerializer, CardChatSerializer
from .models import GeneratedCard, CardSession, CardMessage
from .services.ai_card_drawer import generate_hybrid_business_card
from .services.card_agent import process_card_agent_turn

logger = logging.getLogger(__name__)


class CardChatAPIView(APIView):
    """
    Conversational AI Visiting Card Studio endpoint.
    Supports multi-turn iterative design (like ChatGPT / Gemini).

    POST /api/chat-card/
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
    permission_classes = [HasAPIKey]

    def post(self, request, *args, **kwargs):
        serializer = CardChatSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data.get('session_id')
            message = serializer.validated_data['message']
            try:
                result = process_card_agent_turn(session_id=session_id, user_message=message, request=request)
                return Response(result, status=status.HTTP_200_OK)
            except ValueError as e:
                logger.warning(f"Card chat configuration error: {e}")
                return Response({"status": "error", "error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            except Exception as e:
                logger.error(f"Card chat processing failed: {e}")
                return Response({"status": "error", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CardSessionHistoryAPIView(APIView):
    """
    Retrieves full message history and past versions of a design session.
    GET /api/chat-card/<uuid:session_id>/
    """
    permission_classes = [HasAPIKey]

    def get(self, request, session_id, *args, **kwargs):
        session = CardSession.objects.filter(id=session_id).first()
        if not session:
            return Response({"error": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

        messages_data = []
        for m in session.messages.all():
            messages_data.append({
                "role": m.role,
                "content": m.content,
                "card_data": m.card_data,
                "image_base64": m.image_base64 or m.image_url,
                "image_url": m.image_base64 or m.image_url,
                "version": m.version,
                "created_at": m.created_at.isoformat()
            })

        return Response({
            "session_id": str(session.id),
            "current_version": session.version,
            "current_state": session.current_state,
            "card_data": session.current_state,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "messages": messages_data
        }, status=status.HTTP_200_OK)


class GenerateCardAPIView(APIView):

    """
    API View to generate a professional AI visiting card from a single natural language prompt.

    Request body:
        { "prompt": "Make a visiting card for Md Mamun, Senior Software Engineer at TechVision BD,
                     phone +880 1700-000000, email mamun@techvision.com, website www.techvision.com.bd" }

    Response: PNG image (binary)
    """
    permission_classes = [HasAPIKey]

    def _generate_and_respond(self, prompt: str):
        """Shared logic for GET and POST."""
        try:
            # 3-step pipeline: parse → background → text overlay
            image_bytes, card_data = generate_hybrid_business_card(prompt)
        except ValueError as e:
            logger.warning(f"Card generation configuration error: {e}")
            return Response({"status": "error", "error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f"Card generation failed: {e}")
            return Response({"status": "error", "error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        # Save to PostgreSQL
        phones = card_data.get('phone') or card_data.get('phones') or []
        emails = card_data.get('email') or card_data.get('emails') or []
        websites = card_data.get('websites') or card_data.get('website') or []
        phone_str = ", ".join(phones) if isinstance(phones, (list, tuple)) else str(phones)
        email_str = ", ".join(emails) if isinstance(emails, (list, tuple)) else str(emails)
        website_str = ", ".join(websites) if isinstance(websites, (list, tuple)) else str(websites)

        GeneratedCard.objects.create(
            prompt=prompt,
            name=str(card_data.get('name', '') or ''),
            designation=str(card_data.get('designation', '') or ''),
            phone=phone_str,
            email=email_str,
            website=website_str,
            company_name=str(card_data.get('company_name', '') or ''),
        )

        # Return PNG
        safe_name = card_data.get('name', 'card').replace(' ', '_').lower()[:30]
        response = HttpResponse(image_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="visiting_card_{safe_name}.png"'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['X-User-Prompt'] = urllib.parse.quote(prompt)
        response['X-Card-Data'] = urllib.parse.quote(json.dumps(card_data))
        response['X-AI-Note'] = "AI-generated cards should be manually verified for text accuracy before printing or sharing."
        return response

    def post(self, request, *args, **kwargs):
        serializer = CardPromptSerializer(data=request.data)
        if serializer.is_valid():
            prompt = serializer.validated_data['prompt']
            return self._generate_and_respond(prompt)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, *args, **kwargs):
        """Allows quick GET test with ?prompt=... query param."""
        data = {'prompt': request.query_params.get('prompt', '')}
        serializer = CardPromptSerializer(data=data)
        if serializer.is_valid():
            prompt = serializer.validated_data['prompt']
            return self._generate_and_respond(prompt)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HealthCheckView(APIView):
    """Health check endpoint for Docker container orchestration."""
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return JsonResponse({
            "status": "healthy",
            "service": "AI Visiting Card Generator & Agentic Chat Studio",
            "framework": "Django REST Framework",
            "capabilities": [
                "Single-Shot visiting card generation via POST /api/generate-card/",
                "Multi-Turn Agentic Chat Design via POST /api/chat-card/",
                "Session history & version tracking via GET /api/chat-card/<session_id>/"
            ],
            "endpoints": {
                "chat_agent": "POST /api/chat-card/ with {\"session_id\": \"optional\", \"message\": \"...\"}",
                "single_shot": "POST /api/generate-card/ with {\"prompt\": \"...\"}",
                "health": "GET /api/health/"
            }
        }, status=200)


class OpenAIKeyConfigAPIView(APIView):
    """
    Secure management endpoint for the OpenAI API Key.
    Stores the key with AES-256 Fernet authenticated encryption in the database.
    Allows clients to dynamically rotate/change the OpenAI key via API.

    Protected by HasAPIKey (requires valid X-API-KEY header, Bearer token, or query param).
    """
    permission_classes = [HasAPIKey]

    def get(self, request, *args, **kwargs):
        from card_project.key_manager import get_openai_key_metadata
        metadata = get_openai_key_metadata()
        return Response({
            "success": True,
            **metadata
        }, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        return self._update_key(request)

    def put(self, request, *args, **kwargs):
        return self._update_key(request)

    def _update_key(self, request):
        from card_project.key_manager import (
            set_active_openai_key,
            validate_openai_key_live,
        )
        api_key = request.data.get('api_key') or request.data.get('openai_api_key')
        if not api_key or not isinstance(api_key, str) or not api_key.strip():
            return Response({
                "success": False,
                "error": "The 'api_key' field is required and cannot be empty."
            }, status=status.HTTP_400_BAD_REQUEST)

        api_key = api_key.strip()
        do_validate = request.data.get('validate', True)

        if do_validate:
            is_valid, validation_msg = validate_openai_key_live(api_key)
            if not is_valid:
                return Response({
                    "success": False,
                    "error": validation_msg
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            validation_msg = "Live validation skipped."

        config = set_active_openai_key(api_key)

        return Response({
            "success": True,
            "message": "OpenAI API key encrypted (AES-256) and saved successfully in database.",
            "masked_key": config.masked_key,
            "source": "database",
            "validation_status": validation_msg,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        from card_project.key_manager import clear_active_openai_key, get_openai_key_metadata
        deleted_count = clear_active_openai_key()
        metadata = get_openai_key_metadata()
        return Response({
            "success": True,
            "message": "Database OpenAI key cleared. System reverted to environment default.",
            "records_removed": deleted_count,
            "current_status": metadata
        }, status=status.HTTP_200_OK)
