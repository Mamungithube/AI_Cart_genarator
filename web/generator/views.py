import io
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import CardPromptSerializer, CardChatSerializer
from .models import GeneratedCard, CardSession, CardMessage
from .services.ai_card_drawer import generate_hybrid_business_card
from .services.card_agent import process_card_agent_turn


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
        "image_url": "/media/cards/card_..._v1.png",
      }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CardChatSerializer(data=request.data)
        if serializer.is_valid():
            session_id = serializer.validated_data.get('session_id')
            message = serializer.validated_data['message']
            result = process_card_agent_turn(session_id=session_id, user_message=message, request=request)
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class CardSessionHistoryAPIView(APIView):
    """
    Retrieves full message history and past versions of a design session.
    GET /api/chat-card/<uuid:session_id>/
    """
    permission_classes = [AllowAny]

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
                "image_url": m.image_url,
                "version": m.version,
                "created_at": m.created_at.isoformat()
            })

        return Response({
            "session_id": str(session.id),
            "current_version": session.version,
            "current_state": session.current_state,
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
    permission_classes = [AllowAny]

    def _generate_and_respond(self, prompt: str):
        """Shared logic for GET and POST."""
        # 3-step pipeline: parse → background → text overlay
        image_bytes, card_data = generate_hybrid_business_card(prompt)

        # Save to PostgreSQL
        GeneratedCard.objects.create(
            prompt=prompt,
            name=card_data.get('name', ''),
            designation=card_data.get('designation', ''),
            phone=card_data.get('phone', ''),
            email=card_data.get('email', ''),
            website=card_data.get('website', ''),
            company_name=card_data.get('company_name', ''),
        )

        # Return PNG
        safe_name = card_data.get('name', 'card').replace(' ', '_').lower()[:30]
        response = HttpResponse(image_bytes, content_type='image/png')
        response['Content-Disposition'] = f'inline; filename="visiting_card_{safe_name}.png"'
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
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



