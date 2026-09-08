import os
import cv2
import base64
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .services.cropper import crop_business_card
from .services.enhancer import enhance_card_image
from .services.extractor import extract_with_rotation

logger = logging.getLogger(__name__)


class ProcessCardView(APIView):
    """
    Ported from milo22_image_processing_ai (/process-card).
    Handles business/visiting/credit/ID card photo processing:
      1. Crops card from photo (rembg background removal + contour detection + perspective warp).
      2. Detects rotation via Google Vision (or OpenAI Vision fallback) and rotates upright.
      3. Enhances image quality (denoise, background division, contrast stretch, CLAHE, sharpening).
      4. Extracts structured JSON details via GPT-4o.
      5. Enforces privacy masking on financial cards.
      6. Returns identical JSON response format:
         {
           "success": true,
           "details": { ... },
           "front_image_base64": "...",
           "back_image_base64": "..."
         }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        front_file = request.FILES.get('front')
        back_file = request.FILES.get('back')

        if front_file is None and back_file is None:
            return Response(
                {"success": False, "error": "Please provide at least one image (front or back)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        front_bytes = front_file.read() if front_file else None
        back_bytes = back_file.read() if back_file else None

        vision_api_key = (
            os.environ.get('GOOGLE_VISION_API_KEY') or ''
        ).strip().strip('"').strip("'")

        openai_api_key = (
            os.environ.get('OPENAI_API_KEY') or
            os.environ.get('Open_AI_Key') or
            ''
        ).strip()

        try:
            # 1. Crop cards from photo
            front_bgr = crop_business_card(front_bytes) if front_bytes else None
            back_bgr = crop_business_card(back_bytes) if back_bytes else None

            # 2. Extract structured details & rotate upright
            rotated_front, rotated_back, details = extract_with_rotation(
                front_bgr=front_bgr,
                back_bgr=back_bgr,
                openai_api_key=openai_api_key,
                vision_api_key=vision_api_key
            )

            # 3. Base64 encode rotated/enhanced outputs
            front_b64 = None
            back_b64 = None
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, 85]

            if rotated_front is not None:
                success, buffer = cv2.imencode(".jpg", rotated_front, encode_params)
                if success:
                    front_b64 = base64.b64encode(buffer).decode("utf-8")

            if rotated_back is not None:
                success, buffer = cv2.imencode(".jpg", rotated_back, encode_params)
                if success:
                    back_b64 = base64.b64encode(buffer).decode("utf-8")

            return Response({
                "success": True,
                "details": details,
                "front_image_base64": front_b64,
                "back_image_base64": back_b64
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"process-card failed: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EnhanceCardView(APIView):
    """
    Ported from milo22_image_processing_ai (/enhance-card).
    Enhances card image: 2x upscales, removes shadows, boosts contrast, whitens background, and sharpens text.
    Returns: { "success": true, "enhanced_image_base64": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        image_file = request.FILES.get('image')
        if not image_file:
            return Response(
                {"success": False, "error": "Please provide an image file"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            image_bytes = image_file.read()
            # Decode to numpy BGR
            import numpy as np
            arr = np.frombuffer(image_bytes, np.uint8)
            img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if img_bgr is None:
                return Response(
                    {"success": False, "error": "Invalid image format"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            enhanced = enhance_card_image(img_bgr)
            success, buffer = cv2.imencode(".jpg", enhanced, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                return Response(
                    {"success": False, "error": "Failed to encode image"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            result_b64 = base64.b64encode(buffer).decode("utf-8")
            return Response({
                "success": True,
                "enhanced_image_base64": result_b64
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"enhance-card failed: {e}")
            return Response({
                "success": False,
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
