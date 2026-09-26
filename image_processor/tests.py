import io
import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image, ImageDraw


def _create_test_image():
    img = Image.new('RGB', (400, 250), color=(240, 240, 245))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "Test Business Card", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    buf.name = 'card.jpg'
    buf.seek(0)
    return buf


class ImageProcessorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', '')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.process_url = reverse('api-process-card')
        self.enhance_url = reverse('api-enhance-card')

    def test_unauthorized_without_api_key(self):
        """Request without API key must be blocked with 403."""
        unauth_client = APIClient()
        response = unauth_client.post(self.process_url, data={})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_process_card_empty_returns_400(self):
        """Empty request without front or back must return 400."""
        response = self.client.post(self.process_url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('error', response.data)

    def test_enhance_card_empty_returns_400(self):
        """Request to enhance-card without image file must return 400."""
        response = self.client.post(self.enhance_url, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data.get('success'))
        self.assertIn('error', response.data)

    def test_enhance_card_with_valid_image(self):
        """Enhance card with valid JPEG should return 200 and base64 string."""
        test_file = _create_test_image()
        response = self.client.post(
            self.enhance_url,
            data={'image': test_file},
            format='multipart'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get('success'))
        self.assertTrue(bool(response.data.get('enhanced_image_base64')))

    def test_process_card_missing_openai_key_triggers_notification(self):
        """When OpenAI API key is missing during process-card, returns 503 and notifies webhook."""
        from unittest.mock import patch
        test_file = _create_test_image()

        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            with patch('image_processor.views.send_openai_error_notification') as mock_notify_view:
                response = self.client.post(
                    self.process_url,
                    data={'front': test_file},
                    format='multipart'
                )
                self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
                self.assertFalse(response.data.get('success'))
                mock_notify_view.assert_called()
                msg = str(mock_notify_view.call_args[0][0]).lower()
                self.assertIn("key", msg)

    def test_process_card_openai_error_triggers_notification(self):
        """When OpenAI GPT-4o fails during process-card, notifies webhook."""
        from unittest.mock import patch
        test_file = _create_test_image()

        with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test-key'):
            with patch('image_processor.views.crop_business_card', return_value=None):
                with patch('image_processor.views.extract_with_rotation', side_effect=RuntimeError("OpenAI API error (429): Quota exceeded")):
                    with patch('image_processor.views.send_openai_error_notification') as mock_notify_view:
                        response = self.client.post(
                            self.process_url,
                            data={'front': test_file},
                            format='multipart'
                        )
                        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
                        self.assertFalse(response.data.get('success'))
                        mock_notify_view.assert_called()
