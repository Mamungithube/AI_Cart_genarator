import io
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import CardPromptSerializer
from .models import GeneratedCard
from .services.ai_card_drawer import generate_hybrid_business_card


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
            "service": "AI Visiting Card Generator",
            "framework": "Django REST Framework",
            "pipeline": [
                "Step 0: GPT-4o-mini parses prompt → structured data",
                "Step 1: OpenAI image model → beautiful background art (no text)",
                "Step 2: Pillow → exact text overlay (100% accurate)"
            ],
            "endpoint": "POST /api/generate-card/ with {\"prompt\": \"...\"}",
        }, status=200)
