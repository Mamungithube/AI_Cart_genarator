import io
import os
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from PIL import Image

def make_dummy_png(w=1200, h=700):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), color=(20, 20, 20)).save(buf, format='PNG')
    return buf.getvalue()


class GeneratorAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', '')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.health_url = reverse('health-check')
        self.chat_url = reverse('card-chat')

    def test_unauthorized_without_api_key(self):
        """Request without API key to protected endpoint must return 403."""
        unauth_client = APIClient()
        response = unauth_client.post(self.chat_url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_health_check_endpoint(self):
        """Health check endpoint must return 200 OK without requiring authentication."""
        unauth_client = APIClient()
        response = unauth_client.get(self.health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json().get("status"), "healthy")

    def test_chat_card_missing_message_returns_400(self):
        """Card studio chat requires 'message' field."""
        response = self.client.post(self.chat_url, data={}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.json())


class OpenAIKeyManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', 'card_sec_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.config_url = reverse('api-config-openai-key')

    def test_crypto_roundtrip(self):
        """Verify AES-256 Fernet encryption and decryption accurately restores key."""
        from card_project.key_manager import encrypt_key, decrypt_key
        raw_key = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"
        encrypted = encrypt_key(raw_key)

        # Ciphertext must not match raw key in any way
        self.assertNotEqual(raw_key, encrypted)
        self.assertNotIn(raw_key, encrypted)

        # Decryption must restore identical key
        decrypted = decrypt_key(encrypted)
        self.assertEqual(raw_key, decrypted)

    def test_masking_and_fingerprint(self):
        """Verify safe masking and SHA-256 fingerprint generation."""
        from card_project.key_manager import mask_key, hash_fingerprint
        raw = "sk-proj-1234567890abcdef"
        self.assertEqual(mask_key(raw), "sk-proj...cdef")
        self.assertEqual(len(hash_fingerprint(raw)), 64)

    def test_database_storage_is_encrypted_not_plaintext(self):
        """Verify that the database row never contains plaintext API key."""
        from card_project.key_manager import set_active_openai_key, get_active_openai_key
        from generator.models import OpenAIKeyConfig

        raw_test_key = "sk-proj-topsecretkeyneverleak123456"
        config = set_active_openai_key(raw_test_key)

        # Reload directly from DB
        db_record = OpenAIKeyConfig.objects.get(id=config.id)
        self.assertNotIn(raw_test_key, db_record.encrypted_key)
        self.assertTrue(db_record.encrypted_key.startswith("gAAAAA"))  # Standard Fernet header

        # get_active_openai_key decodes it on demand
        self.assertEqual(get_active_openai_key(), raw_test_key)

    def test_config_endpoint_requires_api_key(self):
        """Unauthenticated requests must be rejected with 403 Forbidden."""
        unauth_client = APIClient()
        get_res = unauth_client.get(self.config_url)
        self.assertEqual(get_res.status_code, status.HTTP_403_FORBIDDEN)

        post_res = unauth_client.post(self.config_url, data={"api_key": "sk-proj-test"}, format='json')
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_config_endpoint_get_post_delete_flow(self):
        """Verify full GET, POST (update key), and DELETE (clear/revert) flow."""
        # 1. GET status
        get_res = self.client.get(self.config_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertTrue(get_res.json()["success"])

        # 2. POST update key (skip live OpenAI network call in unit test)
        new_key = "sk-proj-clientcustomrotatedkey9876543210"
        post_res = self.client.post(
            self.config_url,
            data={"api_key": new_key, "validate": False},
            format='json'
        )
        self.assertEqual(post_res.status_code, status.HTTP_200_OK)
        self.assertTrue(post_res.json()["success"])
        self.assertEqual(post_res.json()["source"], "database")
        self.assertIn("sk-proj...3210", post_res.json()["masked_key"])

        # 3. Verify get_active_openai_key reflects the newly set key
        from card_project.key_manager import get_active_openai_key
        self.assertEqual(get_active_openai_key(), new_key)

        # 4. DELETE to clear DB key and revert to environment
        del_res = self.client.delete(self.config_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertTrue(del_res.json()["success"])
        self.assertNotEqual(get_active_openai_key(), new_key)


class CardAgentBugFixesTests(TestCase):
    def test_detect_style_intent_boundaries(self):
        """Bug 3: Verify English word-boundary regex prevents accidental style overrides."""
        from generator.services.card_agent import detect_style_intent

        # Substrings inside words/emails/URLs must NOT trigger style intent
        self.assertIsNone(detect_style_intent("Please email me at info@techvision.com"))
        self.assertIsNone(detect_style_intent("Company name is GoldenCorp Ltd"))
        self.assertIsNone(detect_style_intent("I work in biotechnology research"))
        self.assertIsNone(detect_style_intent("Address: Marigold Street 42"))
        self.assertIsNone(detect_style_intent("Visit our website at https://techvision.io"))

        # Explicit English style requests MUST trigger style intent
        self.assertEqual(detect_style_intent("Please make it tech style"), 'cyber_tech')
        self.assertEqual(detect_style_intent("Can we switch to cyber tech?"), 'cyber_tech')
        self.assertEqual(detect_style_intent("I need an IT style layout"), 'cyber_tech')
        self.assertEqual(detect_style_intent("Change to luxury gold design"), 'luxury_gold')
        self.assertEqual(detect_style_intent("Use gold borders"), 'luxury_gold')
        self.assertEqual(detect_style_intent("Use corner arcs layout"), 'corner_arcs')
        self.assertEqual(detect_style_intent("Apply organic waves theme"), 'organic_waves')

    def test_infer_layout_style_heuristics(self):
        """Bug 4: Verify single-shot fallback infers distinct layout styles based on profession."""
        from generator.services.ai_card_drawer import infer_layout_style

        self.assertEqual(infer_layout_style(prompt="Software Engineer at OpenAI"), 'cyber_tech')
        self.assertEqual(infer_layout_style(prompt="Python Developer and Tech Lead"), 'cyber_tech')
        self.assertEqual(infer_layout_style(prompt="Managing Director and CEO"), 'luxury_gold')
        self.assertEqual(infer_layout_style(prompt="Senior Partner at Legal Associates"), 'luxury_gold')
        self.assertEqual(infer_layout_style(prompt="Creative Director & Graphic Designer"), 'organic_waves')
        self.assertEqual(infer_layout_style(prompt="Professional Wedding Photographer"), 'organic_waves')
        self.assertEqual(infer_layout_style(prompt="Doctor at Care Medical Hospital"), 'corner_arcs')
        self.assertEqual(infer_layout_style(prompt="Architecture and Real Estate Consultant"), 'corner_arcs')

    def test_new_session_respects_gpt_chosen_style(self):
        """Bug 1: Verify process_card_agent_turn preserves GPT's layout_style on new sessions."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_gpt_state = {
            "name": "Sarah Connor",
            "designation": "AI Engineer",
            "company_name": "Cyberdyne",
            "layout_style": "cyber_tech",
            "theme": {}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=None,
                    user_message="Make a card for Sarah Connor, AI Engineer at Cyberdyne"
                )
                from generator.models import CardSession
                session = CardSession.objects.get(id=result['session_id'])
                # Must be cyber_tech, NOT overridden by round-robin
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')

    def test_existing_session_preserves_design_on_text_edits(self):
        """Bug 3 regression: Editing text with 'techvision' or 'goldencorp' must not alter style."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Bruce Wayne",
                "designation": "Chairman",
                "layout_style": "luxury_gold",
                "theme": {"bg_card": [13, 15, 20]}
            },
            version=1
        )

        mock_updated_state = {
            "name": "Bruce Wayne",
            "designation": "Chairman",
            "company_name": "TechVision BD",
            "email": "bruce@goldencorp.com",
            "layout_style": "luxury_gold",
            "theme": {"bg_card": [13, 15, 20]}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated card.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="Update company to TechVision BD and email to bruce@goldencorp.com"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['layout_style'], 'luxury_gold')

    def test_rollback_restores_previous_style(self):
        """Ensure rollback flow correctly restores earlier version style."""
        from unittest.mock import patch
        from generator.models import CardSession, CardMessage
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Alice",
                "layout_style": "corner_arcs",
                "theme": {"bg_card": [26, 32, 38]}
            },
            version=2
        )
        # Record v1 message with cyber_tech
        CardMessage.objects.create(
            session=session,
            role='assistant',
            content='Initial card',
            card_data={"name": "Alice", "layout_style": "cyber_tech", "theme": {"bg_card": [10, 16, 28]}},
            version=1
        )

        mock_updated_state = {
            "name": "Alice",
            "layout_style": "corner_arcs",
            "theme": {"bg_card": [26, 32, 38]}
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reverted.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="restore previous design"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')

    def test_user_prompt_returned_in_responses(self):
        """Verify user_prompt is returned in process_card_agent_turn and X-User-Prompt in generate-card."""
        import urllib.parse
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        test_msg = "Create a modern visiting card for John Doe"
        mock_state = {"name": "John Doe", "layout_style": "cyber_tech"}

        # 1. Verify process_card_agent_turn returns user_prompt
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message=test_msg)
                self.assertIn("user_prompt", res)
                self.assertEqual(res["user_prompt"], test_msg)

        # 2. Verify CardChatAPIView response contains user_prompt
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created card.", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                chat_res = client.post(chat_url, data={"message": test_msg}, format='json')
                self.assertEqual(chat_res.status_code, status.HTTP_200_OK)
                self.assertIn("user_prompt", chat_res.json())
                self.assertEqual(chat_res.json()["user_prompt"], test_msg)

    def test_card_chat_missing_openai_key_returns_503(self):
        """When OpenAI API key is missing during chat turn, returns 503."""
        from unittest.mock import patch
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            res = client.post(chat_url, data={"message": "Make a card"}, format='json')
            self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(res.json().get("status"), "error")

    def test_card_chat_dalle_failure_returns_502(self):
        """When card image generation fails during chat turn, returns 502."""
        from unittest.mock import patch
        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        mock_state = {"name": "Test User", "layout_style": "cyber_tech"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reasoned", mock_state)):
            with patch('generator.services.card_agent.generate_business_card', side_effect=RuntimeError("AI card generation failed: Render error")):
                res = client.post(chat_url, data={"message": "Make a card"}, format='json')
                self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)
                self.assertEqual(res.json().get("status"), "error")
                self.assertIn("AI card generation failed", res.json().get("error", ""))

    def test_build_precision_dalle_prompt_layout_style_and_theme(self):
        """Verify build_precision_dalle_prompt incorporates layout style description and theme RGBs."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt, LAYOUT_STYLE_DESCRIPTIONS

        spec = {
            "name": "Sarah Connor",
            "designation": "CTO",
            "company_name": "Cyberdyne",
            "layout_style": "cyber_tech",
            "theme": {
                "bg_card": [10, 16, 28],
                "accent": [0, 229, 255],
                "accent_secondary": [56, 189, 248]
            }
        }
        prompt = build_precision_dalle_prompt(spec)
        self.assertIn(LAYOUT_STYLE_DESCRIPTIONS['cyber_tech'], prompt)
        self.assertIn("RGB(10, 16, 28)", prompt)
        self.assertIn("RGB(0, 229, 255)", prompt)
        self.assertIn("RGB(56, 189, 248)", prompt)

        # Fallback when layout_style is not present
        spec_no_style = {
            "name": "John Doe",
            "style_description": "Custom vintage style"
        }
        prompt_fallback = build_precision_dalle_prompt(spec_no_style)
        self.assertIn("Custom vintage style", prompt_fallback)

    def test_color_intent_updates_theme(self):
        """Verify explicit color request preserves GPT's updated theme instead of reverting to current_state."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                "name": "Alice",
                "layout_style": "organic_waves",
                "theme": {"bg_card": [22, 37, 54], "accent": [245, 166, 35]}
            },
            version=1
        )

        red_theme = {"bg_card": [180, 20, 20], "accent": [255, 215, 0], "accent_secondary": [220, 50, 50]}
        mock_updated_state = {
            "name": "Alice",
            "layout_style": "organic_waves",
            "theme": red_theme
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Changed background to red.", mock_updated_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                result = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="change background to red"
                )
                session.refresh_from_db()
                self.assertEqual(session.current_state['theme']['bg_card'], [180, 20, 20])

    def test_phone_number_mandate_in_dalle_prompt(self):
        """Verify prompt contains strict character-by-character mandate for phone number."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        phone_num = "0183774747467463"
        spec = {
            "name": "Bob",
            "phone": phone_num,
            "layout_style": "cyber_tech"
        }
        prompt = build_precision_dalle_prompt(spec)
        self.assertIn(f"CRITICAL PHONE NUMBER MANDATE: render the phone number EXACTLY as '{phone_num}'", prompt)
        self.assertIn("Double-check every single digit matches", prompt)

    def test_note_included_in_responses(self):
        """Verify note is present in chat JSON and X-AI-Note header in generate-card."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_state = {"name": "Test User", "layout_style": "cyber_tech"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card please")
                self.assertIn("note", res)
                self.assertIn("manually verified", res["note"])

        client = APIClient()
        api_key = os.environ.get('API_SECRET_KEY', '')
        client.credentials(HTTP_X_API_KEY=api_key)
        chat_url = reverse('card-chat')

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            gen_res = client.post(chat_url, data={"message": "Visiting card for Bob"}, format='json')
            self.assertEqual(gen_res.status_code, status.HTTP_200_OK)
            self.assertIn('note', gen_res.json())
            self.assertIn("manually verified", gen_res.json()['note'])

    def test_detect_color_intent_precision(self):
        """Verify detect_color_intent only triggers on genuine color instructions, not text containing color words."""
        from generator.services.card_agent import detect_color_intent

        # Genuine color instructions -> True
        self.assertTrue(detect_color_intent("change background to red"))
        self.assertTrue(detect_color_intent("change background to red, keep same layout style"))
        self.assertTrue(detect_color_intent("make it red"))
        self.assertTrue(detect_color_intent("turn it blue"))
        self.assertTrue(detect_color_intent("red background"))
        self.assertTrue(detect_color_intent("accent color green"))
        self.assertTrue(detect_color_intent("dark theme please"))
        self.assertTrue(detect_color_intent("switch color to cyan"))

        # Text edits containing color names as proper nouns or fields -> False
        self.assertFalse(detect_color_intent("add my company name Red Horizon Solutions"))
        self.assertFalse(detect_color_intent("my name is Scarlett Johansson"))
        self.assertFalse(detect_color_intent("company is Blackrock Ltd"))
        self.assertFalse(detect_color_intent("email is john@greenpeace.org"))
        self.assertFalse(detect_color_intent("designation: Light Rail Architect"))
        self.assertFalse(detect_color_intent("Golden Gate Software Inc"))

    def test_company_name_with_color_word_does_not_break_design_stability(self):
        """Verify adding company 'Red Horizon Solutions' does not trigger color intent and preserves layout/theme."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession

        initial_theme = {'bg_card': [26, 32, 38], 'accent': [245, 95, 30], 'accent_secondary': [210, 70, 20]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Mamun Or Rashid',
                'designation': 'Senior Software Engineer',
                'layout_style': 'corner_arcs',
                'theme': initial_theme
            },
            version=1
        )

        # Mock GPT hallucinating cyber_tech and cyan theme on tech company name
        hallucinated_gpt_state = {
            'name': 'Mamun Or Rashid',
            'designation': 'Senior Software Engineer',
            'company_name': 'Red Horizon Solutions',
            'layout_style': 'cyber_tech',
            'theme': {'bg_card': [10, 16, 28], 'accent': [0, 229, 255]}
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Added company.", hallucinated_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(
                    session_id=str(session.id),
                    user_message="add my company name Red Horizon Solutions"
                )
                session.refresh_from_db()
                # Deterministic override MUST preserve corner_arcs and initial_theme
                self.assertEqual(session.current_state['layout_style'], 'corner_arcs')
                self.assertEqual(session.current_state['theme'], initial_theme)
                self.assertEqual(session.current_state['company_name'], 'Red Horizon Solutions')

    def test_repeated_text_only_edits_keep_design_strictly_stable(self):
        """Verify consecutive text-only edits preserve layout_style and theme across multiple turns."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession

        initial_theme = {'bg_card': [22, 37, 54], 'accent': [245, 166, 35], 'accent_secondary': [217, 83, 47]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Original Name',
                'layout_style': 'organic_waves',
                'theme': initial_theme
            },
            version=1
        )

        turns = [
            ("change name to Dr. Strange", {"name": "Dr. Strange", "layout_style": "cyber_tech", "theme": {"bg_card": [0, 0, 0]}}),
            ("add phone 0183774747467463", {"name": "Dr. Strange", "phone": "0183774747467463", "layout_style": "luxury_gold", "theme": {"bg_card": [99, 99, 99]}}),
            ("add address Banani, Dhaka", {"name": "Dr. Strange", "address": "Banani, Dhaka", "layout_style": "corner_arcs", "theme": {"bg_card": [50, 50, 50]}}),
        ]

        with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
            for user_msg, mock_returned_state in turns:
                with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated", mock_returned_state)):
                    process_card_agent_turn(session_id=str(session.id), user_message=user_msg)
                    session.refresh_from_db()
                    # Layout and theme MUST remain organic_waves and initial_theme across all turns
                    self.assertEqual(session.current_state['layout_style'], 'organic_waves')
                    self.assertEqual(session.current_state['theme'], initial_theme)

    def test_image_returned_as_base64_without_saving_to_disk(self):
        """Verify generated card image is returned as base64 without saving files to media directory."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.models import CardSession, CardMessage

        mock_state = {"name": "Alice in Wonderland", "layout_style": "corner_arcs"}
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for Alice")
                self.assertIn("image_base64", res)
                self.assertTrue(res["image_base64"].startswith("data:image/png;base64,"))
                self.assertEqual(res["image_url"], res["image_base64"])

                # Check that CardMessage stores base64 string
                msg = CardMessage.objects.filter(session_id=res["session_id"]).order_by('-created_at').first()
                self.assertIsNotNone(msg)
                self.assertTrue(msg.image_base64.startswith("data:image/png;base64,"))

    def test_card_data_returned_in_chat_response(self):
        """Verify card_data dictionary is included directly in the chat response and history."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_state = {
            "name": "Bruce Wayne",
            "designation": "Chairman",
            "company_name": "Wayne Enterprises",
            "layout_style": "luxury_gold"
        }
        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", mock_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for Bruce")
                self.assertIn("card_data", res)
                self.assertEqual(res["card_data"]["name"], "Bruce Wayne")
                self.assertEqual(res["card_data"]["company_name"], "Wayne Enterprises")
                self.assertEqual(res["card_data"]["layout_style"], "luxury_gold")

    def test_multiple_phones_and_emails_as_array(self):
        """Verify phone and email support multiple items in array format across card_data and prompt."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        multiple_state = {
            "name": "Dr. Mamun",
            "phone": ["+880 1837000000", "+880 1700111222"],
            "email": ["mamun@techvision.com", "info@mamun.dev"],
            "layout_style": "cyber_tech"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", multiple_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card with 2 phones and 2 emails")
                card_data = res["card_data"]

                # Check phone is list
                self.assertIsInstance(card_data["phone"], list)
                self.assertEqual(len(card_data["phone"]), 2)
                self.assertIn("+880 1837000000", card_data["phone"])
                self.assertIn("+880 1700111222", card_data["phone"])

                # Check email is list
                self.assertIsInstance(card_data["email"], list)
                self.assertEqual(len(card_data["email"]), 2)
                self.assertIn("mamun@techvision.com", card_data["email"])
                self.assertIn("info@mamun.dev", card_data["email"])

                # Check prompt contains both phones and emails
                prompt = build_precision_dalle_prompt(card_data)
                self.assertIn("+880 1837000000", prompt)
                self.assertIn("+880 1700111222", prompt)
                self.assertIn("mamun@techvision.com", prompt)
                self.assertIn("info@mamun.dev", prompt)

    def test_comma_separated_contacts_normalized_to_array(self):
        """Verify string inputs with multiple comma-separated contacts are cleanly normalized to arrays."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        string_contacts_state = {
            "name": "John Doe",
            "phone": "01837747474, 01711223344",
            "email": "john@doe.com, john.work@corp.io",
            "layout_style": "corner_arcs"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created", string_contacts_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for John")
                card_data = res["card_data"]
                self.assertEqual(card_data["phone"], ["01837747474", "01711223344"])
                self.assertEqual(card_data["email"], ["john@doe.com", "john.work@corp.io"])

    def test_single_shot_multiple_contacts_generation(self):
        """Verify single-shot generate_hybrid_business_card extracts and formats multiple contacts as lists."""
        from unittest.mock import patch
        from generator.services.ai_card_drawer import generate_hybrid_business_card

        mock_spec = {
            "name": "Jane Doe",
            "phone": ["01837747474", "01711223344"],
            "email": ["jane@work.com", "jane@personal.com"],
            "layout_style": "cyber_tech"
        }
        with patch('generator.services.ai_card_drawer.analyze_and_design_card', return_value=mock_spec):
            with patch('generator.services.ai_card_drawer.generate_dalle_card', return_value=make_dummy_png()):
                with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test'):
                    img_bytes, card_data = generate_hybrid_business_card("Jane Doe with 2 phones and 2 emails")
                    self.assertIsInstance(card_data["phone"], list)
                    self.assertEqual(card_data["phone"], ["01837747474", "01711223344"])
                    self.assertIsInstance(card_data["email"], list)
                    self.assertEqual(card_data["email"], ["jane@work.com", "jane@personal.com"])

    def test_comprehensive_visiting_card_fields_json(self):
        """Verify all possible visiting card data fields exist in JSON response and prompt."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        full_doctor_card = {
            "name": "Dr. Sarah Connor",
            "designation": "Chief Cardiac Surgeon & Professor",
            "department": "Department of Cardiology",
            "qualifications": ["MBBS (DMC)", "FCPS (Surgery)", "FRCS (Glasgow)"],
            "company_name": "Apollo Heart Institute",
            "tagline": "Excellence in Cardiovascular Care",
            "phone": ["+880 1812345678", "+880 1798765432"],
            "email": ["dr.sarah@apolloheart.org", "sarah.personal@med.com"],
            "website": ["https://apolloheart.org", "https://drsarahconnor.med"],
            "address": "Plot 15, Road 71, Gulshan-2",
            "branch": "Main Hospital Campus",
            "city": "Dhaka",
            "postal_code": "1212",
            "country": "Bangladesh",
            "schedule": "Saturday to Wednesday: 5:00 PM - 9:00 PM",
            "services": ["Bypass Surgery", "Angioplasty", "Valve Replacement"],
            "social_links": {
                "linkedin": "https://linkedin.com/in/drsarah",
                "github": "",
                "twitter": "@drsarahconnor",
                "facebook": "https://facebook.com/drsarah.cardiac",
                "instagram": "",
                "youtube": "https://youtube.com/@drsarahconnor"
            },
            "layout_style": "luxury_gold"
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created full profile card", full_doctor_card)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Create full doctor card")
                data = res["card_data"]

                # 1. Identity & Credentials
                self.assertEqual(data["name"], "Dr. Sarah Connor")
                self.assertEqual(data["designation"], "Chief Cardiac Surgeon & Professor")
                self.assertEqual(data["department"], "Department of Cardiology")
                self.assertEqual(data["qualifications"], ["MBBS (DMC)", "FCPS (Surgery)", "FRCS (Glasgow)"])
                self.assertEqual(data["monogram"], "DS")

                # 2. Organization & Slogan
                self.assertEqual(data["company_name"], "Apollo Heart Institute")
                self.assertEqual(data["tagline"], "Excellence in Cardiovascular Care")

                # 3. Multi-value Contacts
                self.assertEqual(data["phone"], ["+880 1812345678", "+880 1798765432"])
                self.assertEqual(data["phones"], ["+880 1812345678", "+880 1798765432"])
                self.assertEqual(data["email"], ["dr.sarah@apolloheart.org", "sarah.personal@med.com"])
                self.assertEqual(data["emails"], ["dr.sarah@apolloheart.org", "sarah.personal@med.com"])
                self.assertEqual(data["website"], "https://apolloheart.org")
                self.assertEqual(data["websites"], ["https://apolloheart.org", "https://drsarahconnor.med"])

                # 4. Location & Address
                self.assertEqual(data["address"], "Plot 15, Road 71, Gulshan-2")
                self.assertEqual(data["branch"], "Main Hospital Campus")
                self.assertEqual(data["city"], "Dhaka")
                self.assertEqual(data["postal_code"], "1212")
                self.assertEqual(data["country"], "Bangladesh")

                # 5. Operational Details & Services
                self.assertEqual(data["schedule"], "Saturday to Wednesday: 5:00 PM - 9:00 PM")
                self.assertEqual(data["services"], ["Bypass Surgery", "Angioplasty", "Valve Replacement"])

                # 6. Social Profiles
                self.assertIn("linkedin", data["social_links"])
                self.assertEqual(data["social_links"]["linkedin"], "https://linkedin.com/in/drsarah")
                self.assertEqual(data["linkedin"], "https://linkedin.com/in/drsarah")
                self.assertEqual(data["twitter"], "@drsarahconnor")

                # 7. Verify DALL-E prompt synthesis includes all fields
                prompt = build_precision_dalle_prompt(data)
                self.assertIn("Dr. Sarah Connor", prompt)
                self.assertIn("Chief Cardiac Surgeon & Professor", prompt)
                self.assertIn("MBBS (DMC)", prompt)
                self.assertIn("Excellence in Cardiovascular Care", prompt)
                self.assertIn("Apollo Heart Institute", prompt)
                self.assertIn("+880 1812345678", prompt)
                self.assertIn("dr.sarah@apolloheart.org", prompt)
                self.assertIn("https://apolloheart.org", prompt)
                self.assertIn("Saturday to Wednesday", prompt)
                self.assertIn("Bypass Surgery", prompt)


class OpenAINotificationTests(TestCase):
    """
    Tests for the OpenAI error notification webhook:
    POST https://server.milo22.cloud/api/notifications/openai-notification
    X-API-KEY: notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a
    Body: {"message": "..."}
    """
    def setUp(self):
        self.client = APIClient()
        self.api_key = os.environ.get('API_SECRET_KEY', '')
        self.client.credentials(HTTP_X_API_KEY=self.api_key)
        self.chat_url = reverse('card-chat')

    def test_notification_service_payload_and_headers(self):
        """send_openai_error_notification must deliver the correct URL, headers, and body."""
        from unittest.mock import patch
        from card_project.notifications import send_openai_error_notification

        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            test_error = "OpenAI API rate limit exceeded: quota 429"
            send_openai_error_notification(test_error, async_send=False)

            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            self.assertEqual(args[0], "https://server.milo22.cloud/api/notifications/openai-notification")
            self.assertEqual(kwargs['headers']['X-API-KEY'], "notification_ai_9a7d3e5f1b2c4d8e0f6a5b4c3d2e1f0a")
            self.assertEqual(kwargs['json']['message'], test_error)

    def test_card_chat_missing_openai_key_triggers_notification(self):
        """When OpenAI API key is missing during chat, notification webhook must be triggered."""
        from unittest.mock import patch

        with patch('card_project.key_manager.get_active_openai_key', return_value=''):
            with patch('generator.views.send_openai_error_notification') as mock_notify_view, \
                 patch('generator.services.card_agent.send_openai_error_notification') as mock_notify_agent:
                response = self.client.post(self.chat_url, data={"message": "Create a modern visiting card"}, format='json')
                self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
                self.assertTrue(mock_notify_view.called or mock_notify_agent.called)

    def test_card_chat_openai_error_triggers_notification(self):
        """When OpenAI API fails (e.g. 429 Insufficient Quota), notification webhook must be triggered."""
        from unittest.mock import patch

        with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test-valid-key'):
            with patch('generator.services.card_agent.reason_card_modifications', side_effect=RuntimeError("RateLimitError: 429 Insufficient Quota")):
                with patch('generator.services.card_agent.send_openai_error_notification') as mock_notify_agent, \
                     patch('generator.views.send_openai_error_notification') as mock_notify_view:
                    response = self.client.post(self.chat_url, data={"message": "Visiting card for Alice"}, format='json')
                    self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
                    self.assertTrue(mock_notify_agent.called or mock_notify_view.called)

    def test_notification_network_failure_is_resilient(self):
        """Even if webhook endpoint fails or times out, the notification service does not crash."""
        from unittest.mock import patch
        import requests
        from card_project.notifications import send_openai_error_notification

        with patch('requests.post', side_effect=requests.exceptions.ConnectTimeout("Connection timed out")):
            result = send_openai_error_notification("Some OpenAI error", async_send=False)
            self.assertFalse(result)


class CardCompositionAndRedesignIntentTests(TestCase):
    """
    Tests for:
    1. Redesign / Dissatisfaction Intent detection & priority bypass.
    2. Structural composition diversity with COMPOSITION_VARIANTS.
    3. Strict preservation of (layout_style, theme, composition_variant) on text-only edits.
    4. Rollback restoring composition_variant from previous version.
    5. Fallback on invalid/fabricated composition_variant from GPT.
    """

    def test_detect_redesign_intent_matches_all_required_phrases(self):
        """Verify detect_redesign_intent catches explicit redesign & dissatisfaction signals."""
        from generator.services.card_agent import detect_redesign_intent

        explicit_phrases = [
            "redesign this",
            "I want a different design please",
            "give it a fresh look",
            "give me a new look for the card",
            "change the design now",
            "make it look different please",
            "redesign this completely",
        ]
        for phrase in explicit_phrases:
            self.assertTrue(detect_redesign_intent(phrase), f"Failed to match explicit phrase: {phrase}")

        dissatisfaction_phrases = [
            "this design is very bad",
            "this design is bad",
            "i don't like this",
            "i dont like it",
            "not good",
            "looks bad",
            "don't like the design",
            "hate this design",
            "this looks bad",
            "not what i wanted",
            "can you make it better",
            "this isn't good",
            "this isnt good",
        ]
        for phrase in dissatisfaction_phrases:
            self.assertTrue(detect_redesign_intent(phrase), f"Failed to match dissatisfaction phrase: {phrase}")

        # Text edits and normal prompts must NOT trigger redesign intent
        normal_phrases = [
            "change name to John Doe",
            "add phone 01837747474",
            "my company is Badshah Foods",
            "change address to Banani Dhaka",
            "make it red",
        ]
        for phrase in normal_phrases:
            self.assertFalse(detect_redesign_intent(phrase), f"False positive redesign intent on: {phrase}")

    def test_redesign_intent_dissatisfaction_changes_all_three(self):
        """User saying 'this design is very bad' changes layout_style, theme, and composition_variant."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        initial_theme = {'bg_card': [22, 37, 54], 'accent': [245, 166, 35]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Michael Chen',
                'designation': 'Senior Financial Advisor',
                'company_name': 'Wealth Plus',
                'layout_style': 'luxury_gold',
                'theme': initial_theme,
                'composition_variant': 'centered_hero',
            },
            version=1
        )

        mock_gpt_state = {
            'name': 'Michael Chen',
            'designation': 'Senior Financial Advisor',
            'company_name': 'Wealth Plus',
            'layout_style': 'cyber_tech',
            'theme': {'bg_card': [10, 16, 28], 'accent': [0, 229, 255]},
            'composition_variant': 'split_diagonal',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Redesigned card.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="this design is very bad")
                session.refresh_from_db()
                # All 3 visual attributes MUST have changed from previous state
                self.assertNotEqual(session.current_state['layout_style'], 'luxury_gold')
                self.assertNotEqual(session.current_state['theme'], initial_theme)
                self.assertNotEqual(session.current_state['composition_variant'], 'centered_hero')
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')
                self.assertEqual(session.current_state['composition_variant'], 'split_diagonal')

    def test_redesign_intent_explicit_redesign_changes_all_three(self):
        """User saying 'redesign this completely' changes layout_style, theme, and composition_variant."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                'name': 'Sarah Connor',
                'layout_style': 'corner_arcs',
                'theme': {'bg_card': [26, 32, 38]},
                'composition_variant': 'left_monogram_stack',
            },
            version=1
        )

        # Even if GPT gave the same layout_style and empty composition_variant, round-robin ensures they change
        mock_gpt_state = {
            'name': 'Sarah Connor',
            'layout_style': 'corner_arcs',
            'composition_variant': '',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Redesigned.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="redesign this completely")
                session.refresh_from_db()
                self.assertNotEqual(session.current_state['layout_style'], 'corner_arcs')
                self.assertNotEqual(session.current_state['composition_variant'], 'left_monogram_stack')

    def test_color_intent_preserves_layout_style_and_composition_variant(self):
        """'make it red' updates theme, but strictly preserves layout_style and composition_variant."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        initial_theme = {'bg_card': [22, 37, 54], 'accent': [245, 166, 35]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Tony Stark',
                'layout_style': 'cyber_tech',
                'theme': initial_theme,
                'composition_variant': 'split_diagonal',
            },
            version=1
        )

        red_theme = {'bg_card': [139, 0, 0], 'accent': [255, 69, 0]}
        mock_gpt_state = {
            'name': 'Tony Stark',
            'layout_style': 'luxury_gold',  # GPT attempts to alter style
            'theme': red_theme,
            'composition_variant': 'top_banner',  # GPT attempts to alter composition
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated colors.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="make it red")
                session.refresh_from_db()
                # Theme updated to red
                self.assertEqual(session.current_state['theme'], red_theme)
                # Layout style and composition variant strictly preserved!
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')
                self.assertEqual(session.current_state['composition_variant'], 'split_diagonal')

    def test_text_only_edits_strictly_preserve_all_three(self):
        """Text edits like adding phone or company strictly preserve layout_style, theme, and composition_variant."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        initial_theme = {'bg_card': [13, 15, 20], 'accent': [212, 175, 55]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Bruce Wayne',
                'company_name': 'Wayne Enterprises',
                'layout_style': 'luxury_gold',
                'theme': initial_theme,
                'composition_variant': 'asymmetric_offset',
            },
            version=1
        )

        # Mock GPT output attempting to change style, theme, and composition
        mock_gpt_state = {
            'name': 'Bruce Wayne',
            'company_name': 'Wayne Enterprises',
            'phone': ['01837747474'],
            'layout_style': 'organic_waves',
            'theme': {'bg_card': [0, 0, 0]},
            'composition_variant': 'centered_hero',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Added phone.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="add my phone number 01837747474")
                session.refresh_from_db()
                self.assertEqual(session.current_state['phone'], ['01837747474'])
                self.assertEqual(session.current_state['layout_style'], 'luxury_gold')
                self.assertEqual(session.current_state['theme'], initial_theme)
                self.assertEqual(session.current_state['composition_variant'], 'asymmetric_offset')

    def test_rollback_restores_previous_composition_variant(self):
        """Rollback restores the earlier version's composition_variant as well as layout_style."""
        from unittest.mock import patch
        from generator.models import CardSession, CardMessage
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                'name': 'Clark Kent',
                'layout_style': 'corner_arcs',
                'theme': {'bg_card': [26, 32, 38]},
                'composition_variant': 'right_aligned_monogram',
            },
            version=2
        )

        # V1 had cyber_tech with centered_hero
        CardMessage.objects.create(
            session=session,
            role='assistant',
            content='Initial design',
            card_data={
                'name': 'Clark Kent',
                'layout_style': 'cyber_tech',
                'theme': {'bg_card': [10, 16, 28]},
                'composition_variant': 'centered_hero',
            },
            version=1
        )

        mock_gpt_state = {
            'name': 'Clark Kent',
            'layout_style': 'corner_arcs',
            'composition_variant': 'right_aligned_monogram',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reverted.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="bring back the previous design")
                session.refresh_from_db()
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')
                self.assertEqual(session.current_state['composition_variant'], 'centered_hero')

    def test_invalid_composition_variant_falls_back_cleanly(self):
        """Fabricated or typo composition_variant from GPT falls back cleanly and is never in prompt or state."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn
        from generator.services.ai_card_drawer import COMPOSITION_VARIANTS, build_precision_dalle_prompt

        # GPT sends hallucinated variant 'crazy_diagonal_split_hero'
        mock_gpt_state = {
            'name': 'Diana Prince',
            'layout_style': 'organic_waves',
            'composition_variant': 'crazy_diagonal_split_hero',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=None, user_message="Card for Diana Prince")
                variant = res['card_data']['composition_variant']
                self.assertIn(variant, COMPOSITION_VARIANTS)
                self.assertNotEqual(variant, 'crazy_diagonal_split_hero')

                # Verify DALL-E prompt does not contain the fabricated string and contains valid MANDATORY COMPOSITION
                prompt = build_precision_dalle_prompt(res['card_data'])
                self.assertNotIn('crazy_diagonal_split_hero', prompt)
                self.assertIn('MANDATORY COMPOSITION:', prompt)

    def test_build_precision_dalle_prompt_includes_composition_mandate(self):
        """Verify build_precision_dalle_prompt injects the correct composition description."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt, COMPOSITION_VARIANTS

        for key, desc in COMPOSITION_VARIANTS.items():
            card_spec = {
                'name': 'John Tester',
                'layout_style': 'corner_arcs',
                'composition_variant': key
            }
            prompt = build_precision_dalle_prompt(card_spec)
            self.assertIn(f"MANDATORY COMPOSITION: {desc}.", prompt)

    def test_same_profession_distinct_sessions_composition_diversity(self):
        """Verify different prompts for same profession yield diverse composition variants."""
        from generator.services.card_agent import process_card_agent_turn
        from unittest.mock import patch

        prompts = [
            "Michael Chen, Senior Financial Advisor at Wealth Plus, mchen@wealthplus.com",
            "David Vance, Senior Financial Advisor at Capital Growth, dvance@growth.com",
            "Alice Miller, Wealth Advisor at Apex Partners, amiller@apex.org",
            "Robert Sterling, Financial Consultant at First Asset, rsterling@asset.com",
        ]

        compositions = set()
        with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
            for prompt in prompts:
                mock_state = {"name": prompt.split(',')[0], "layout_style": "luxury_gold"}
                with patch('generator.services.card_agent.reason_card_modifications', return_value=("Created.", mock_state)):
                    res = process_card_agent_turn(session_id=None, user_message=prompt)
                    comp = res['card_data'].get('composition_variant')
                    self.assertIsNotNone(comp)
                    compositions.add(comp)

        # Diverse composition variants must be generated (more than 1 distinct variant)
        self.assertGreater(len(compositions), 1)

    def test_conflict_redesign_wins_over_color_intent(self):
        """When both is_redesign_intent and is_color_intent are True, redesign hierarchy wins.
        (both layout_style and composition_variant change, not preserved like in color-only intent).
        """
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import (
            detect_color_intent,
            detect_redesign_intent,
            process_card_agent_turn,
        )

        test_msg = "this red design is very bad, change it completely"

        # 1. Verify both intents are True simultaneously
        self.assertTrue(detect_color_intent(test_msg), "Expected is_color_intent to be True")
        self.assertTrue(detect_redesign_intent(test_msg), "Expected is_redesign_intent to be True")

        # 2. Set up initial session
        initial_theme = {'bg_card': [139, 0, 0], 'accent': [255, 69, 0]}
        session = CardSession.objects.create(
            current_state={
                'name': 'Alexander Pierce',
                'layout_style': 'corner_arcs',
                'theme': initial_theme,
                'composition_variant': 'left_monogram_stack',
            },
            version=1
        )

        # Mock GPT output
        mock_gpt_state = {
            'name': 'Alexander Pierce',
            'layout_style': 'cyber_tech',
            'theme': {'bg_card': [10, 16, 28], 'accent': [0, 229, 255]},
            'composition_variant': 'centered_hero',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Completely redesigned.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message=test_msg)
                session.refresh_from_db()

                # Redesign hierarchy MUST win:
                # layout_style MUST change (NOT preserved as corner_arcs)
                self.assertNotEqual(session.current_state['layout_style'], 'corner_arcs')
                self.assertEqual(session.current_state['layout_style'], 'cyber_tech')

                # composition_variant MUST change (NOT preserved as left_monogram_stack)
                self.assertNotEqual(session.current_state['composition_variant'], 'left_monogram_stack')
                self.assertEqual(session.current_state['composition_variant'], 'centered_hero')

                # theme MUST also update to new design
                self.assertNotEqual(session.current_state['theme'], initial_theme)

    def test_rollback_pre_migration_message_without_composition_variant_key(self):
        """Pre-migration CardMessage without composition_variant key safely falls back to left_monogram_stack without error."""
        from unittest.mock import patch
        from generator.models import CardSession, CardMessage
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                'name': 'Hal Jordan',
                'layout_style': 'luxury_gold',
                'theme': {'bg_card': [13, 15, 20]},
                'composition_variant': 'asymmetric_offset',
            },
            version=2
        )

        # Pre-migration card_data: NO composition_variant key at all!
        CardMessage.objects.create(
            session=session,
            role='assistant',
            content='Old design before migration',
            card_data={
                'name': 'Hal Jordan',
                'layout_style': 'organic_waves',
                'theme': {'bg_card': [22, 37, 54]},
                # composition_variant intentionally missing!
            },
            version=1
        )

        mock_gpt_state = {
            'name': 'Hal Jordan',
            'layout_style': 'luxury_gold',
            'composition_variant': 'asymmetric_offset',
        }

        with patch('generator.services.card_agent.reason_card_modifications', return_value=("Reverted.", mock_gpt_state)):
            with patch('generator.services.card_agent.generate_dalle_card', return_value=make_dummy_png()):
                res = process_card_agent_turn(session_id=str(session.id), user_message="bring back previous design")
                session.refresh_from_db()

                # Restores style from v1
                self.assertEqual(session.current_state['layout_style'], 'organic_waves')
                # Safely defaults composition_variant to 'left_monogram_stack' without KeyError/crash
                self.assertEqual(session.current_state['composition_variant'], 'left_monogram_stack')

    def test_text_safe_zone_and_anti_frame_prompt_with_long_name(self):
        """Verify prompt with long name includes non-conflicting safe zone and anti-frame mandates."""
        from generator.services.ai_card_drawer import build_precision_dalle_prompt

        long_name_spec = {
            'name': 'Dr. Kamal Hossain',
            'designation': 'Senior Supreme Court Advocate & Constitutional Jurist',
            'company_name': 'Kamal Hossain & Associates',
            'layout_style': 'luxury_gold',
            'composition_variant': 'centered_hero',
        }
        prompt = build_precision_dalle_prompt(long_name_spec)

        # 1. Exact text is present
        self.assertIn("Name: 'Dr. Kamal Hossain'", prompt)
        self.assertIn("Title: 'Senior Supreme Court Advocate & Constitutional Jurist'", prompt)

        # 2. Text Safe Zone mandate is present
        self.assertIn("MANDATORY TEXT SAFE ZONE (DO NOT CONFUSE WITH CANVAS SIZE)", prompt)
        self.assertIn("The card's background graphic, color, and decorative pattern MUST still fill 100%", prompt)
        self.assertIn("The safe-zone rule applies ONLY to where TEXT CHARACTERS are placed", prompt)
        self.assertIn("do NOT shrink, frame, or pad the overall card graphic itself", prompt)

        # 3. Canvas Mandate and Anti-Frame reinforcement are present
        self.assertIn("CANVAS MANDATE: Edge-to-edge flat 2D digital print file filling 100% of the 1536x1024 frame with zero outer margins.", prompt)
        self.assertIn("ABSOLUTELY NO visible outer canvas border, no white/empty padding strip, no card-within-a-frame appearance", prompt)

    def test_auto_crop_is_noop_on_full_bleed_card(self):
        """When the card fills the entire image without outer borders, auto_crop_card_surface is a no-op."""
        from generator.services.ai_card_drawer import auto_crop_card_surface
        from PIL import Image
        import io

        # Create a full-bleed 1536x1024 card without outer background borders
        buf = io.BytesIO()
        img = Image.new('RGB', (1536, 1024), color=(22, 37, 54))
        img.save(buf, format='PNG')
        raw_bytes = buf.getvalue()

        # auto_crop should detect no outer boundary and return raw_bytes unmodified
        cropped_bytes = auto_crop_card_surface(raw_bytes)
        self.assertEqual(cropped_bytes, raw_bytes)


class VectorCardDrawerTests(TestCase):
    """
    Comprehensive tests for the PIL/Pillow-based deterministic vector business card engine.
    Verifies pixel-perfect 1200x700 rendering, all 4 styles, and all 6 composition variants.
    """

    def setUp(self):
        self.sample_card_data = {
            'name': 'Dr. Mamun Rashid',
            'designation': 'Lead AI Systems Architect',
            'company_name': 'Quantum Innovations Ltd',
            'phone': '+880 1700-123456',
            'email': 'mamun@quantum-ai.com',
            'website': 'quantum-ai.com',
            'address': 'Gulshan 2, Dhaka, Bangladesh',
            'schedule': 'Sun-Thu 9:00 AM - 6:00 PM',
        }

    def test_all_styles_and_composition_variants_render_png(self):
        """All 4 styles x 6 composition variants render valid 1200x700 PNGs without error."""
        from generator.services.card_drawer import generate_business_card, COMPOSITION_RENDERERS
        styles = ['cyber_tech', 'corner_arcs', 'luxury_gold', 'organic_waves']
        variants = list(COMPOSITION_RENDERERS.keys())

        for style in styles:
            for variant in variants:
                data = dict(self.sample_card_data)
                data['layout_style'] = style
                data['composition_variant'] = variant
                png_bytes = generate_business_card(data)

                self.assertIsInstance(png_bytes, bytes)
                self.assertGreater(len(png_bytes), 5000, f"Rendered card too small for {style} - {variant}")

                # Open with PIL to verify valid PNG and exact canvas dimensions
                img = Image.open(io.BytesIO(png_bytes))
                self.assertEqual(img.format, 'PNG')
                self.assertEqual(img.size, (1200, 700))

    def test_turn_uses_vector_engine_and_returns_base64(self):
        """Card agent turn produces deterministic PNG base64 via vector drawer in sub-second time."""
        from unittest.mock import patch
        from generator.services.card_agent import process_card_agent_turn

        mock_state = {
            'name': 'Alice Smith',
            'designation': 'Principal Designer',
            'company_name': 'DesignStudio X',
            'phone': '+1 555-0199',
            'email': 'alice@designstudio.io',
            'layout_style': 'luxury_gold',
            'composition_variant': 'split_diagonal',
        }

        with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test-valid-key'):
            with patch('generator.services.card_agent.reason_card_modifications', return_value=("Card designed successfully.", mock_state)):
                result = process_card_agent_turn(session_id=None, user_message="Make a card for Alice Smith")

                self.assertEqual(result['status'], 'success')
                self.assertTrue(result['image_base64'].startswith('data:image/png;base64,'))
                self.assertEqual(result['card_data']['layout_style'], 'luxury_gold')
                self.assertEqual(result['card_data']['composition_variant'], 'split_diagonal')
                self.assertIn('_python_code', result['card_data'])


class DynamicCardCoderTests(TestCase):
    """
    Tests for ChatGPT Code Interpreter style dynamic AI code generation and sandbox execution.
    """

    def test_sandbox_execution_produces_1200x700_png(self):
        """Execution of valid Pillow code in sandbox yields valid 1200x700 PNG."""
        from generator.services.dynamic_card_coder import build_default_fallback_code, execute_card_code
        data = {
            'name': 'Dr. Robert Oppenheimer',
            'designation': 'Director of Theoretical Physics',
            'company_name': 'Institute for Advanced Study',
            'phone': '+1 609-734-8000',
            'email': 'oppenheimer@ias.edu',
        }
        code = build_default_fallback_code(data)
        png_bytes, working_code = execute_card_code(code)

        self.assertIsInstance(png_bytes, bytes)
        self.assertGreater(len(png_bytes), 5000)

        img = Image.open(io.BytesIO(png_bytes))
        self.assertEqual(img.format, 'PNG')
        self.assertEqual(img.size, (1200, 700))
        self.assertIn('def draw_visiting_card', working_code)

    def test_sandbox_security_blocks_unauthorized_builtins(self):
        """Sandbox blocks file system access and system imports."""
        from generator.services.dynamic_card_coder import execute_card_code
        unsafe_code = """def draw_visiting_card(fonts):
    f = open('/tmp/unauthorized.txt', 'w')
    return Image.new('RGB', (1200, 700))
"""
        with self.assertRaises(RuntimeError) as ctx:
            execute_card_code(unsafe_code, api_key=None, max_retries=0)
        self.assertIn("NameError", str(ctx.exception))

    def test_self_healing_retry_loop_recovers_from_syntax_error(self):
        """When code fails, self-healing loop calls healer and produces valid PNG."""
        from unittest.mock import patch
        from generator.services.dynamic_card_coder import execute_card_code, build_default_fallback_code

        broken_code = """def draw_visiting_card(fonts):
    x = 1 / 0  # ZeroDivisionError
    return Image.new('RGB', (1200, 700))
"""
        fixed_code = build_default_fallback_code({'name': 'Healed Card'})
        with patch('generator.services.dynamic_card_coder.heal_card_code', return_value=fixed_code) as mock_healer:
            png_bytes, final_code = execute_card_code(broken_code, api_key='sk-test-key', max_retries=1)
            self.assertTrue(mock_healer.called)
            self.assertGreater(len(png_bytes), 5000)
            self.assertIn('Healed Card', final_code)

    def test_multi_turn_code_continuity(self):
        """Turn 2 refines existing code rather than rewriting it from scratch."""
        from unittest.mock import patch
        from generator.models import CardSession
        from generator.services.card_agent import process_card_agent_turn

        session = CardSession.objects.create(
            current_state={
                'name': 'Original Name',
                'phone': '+1 555-0100',
                '_python_code': 'def draw_visiting_card(fonts):\n    return Image.new("RGB", (1200, 700), (20, 20, 20))\n'
            },
            version=1
        )

        mock_state = {
            'name': 'Original Name',
            'phone': '+1 555-0999',
            'layout_style': 'organic_waves',
        }

        with patch('card_project.key_manager.get_active_openai_key', return_value='sk-test-key'):
            with patch('generator.services.card_agent.reason_card_modifications', return_value=("Updated phone.", mock_state)):
                with patch('generator.services.card_agent.refine_card_code', return_value='def draw_visiting_card(fonts):\n    return Image.new("RGB", (1200, 700), (30, 30, 30))\n') as mock_refiner:
                    res = process_card_agent_turn(session_id=str(session.id), user_message="change phone to +1 555-0999")
                    self.assertTrue(mock_refiner.called)
                    self.assertEqual(res['status'], 'success')
                    self.assertTrue(res['image_base64'].startswith('data:image/png;base64,'))






