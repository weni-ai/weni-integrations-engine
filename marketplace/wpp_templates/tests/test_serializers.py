from unittest.mock import MagicMock, patch
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from rest_framework import serializers as drf_serializers

from marketplace.wpp_templates.serializers import (
    TemplateTranslationSerializer,
    TemplateMessageSerializer,
)


class TestTemplateTranslationSerializer(TestCase):
    """Unit tests for TemplateTranslationSerializer covering component building and persistence."""

    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_create_basic_components_and_persistence(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        """Ensures basic body/footer/buttons assemble and persistence calls occur."""
        # Arrange template instance and service
        template_instance = MagicMock()
        template_instance.name = "t-name"
        template_instance.category = "UTILITY"
        template_instance.app.config = {"wa_waba_id": "waba-xyz"}
        template_instance.app.apptype.get_access_token.return_value = "acc-1"
        mock_template_message.objects.get.return_value = template_instance

        svc_instance = MagicMock()
        svc_instance.create_template_message.return_value = {"id": "mid-1"}
        mock_template_service_cls.return_value = svc_instance

        translation_obj = MagicMock()
        mock_template_translation.objects.create.return_value = translation_obj

        serializer = TemplateTranslationSerializer()
        validated = {
            "template_uuid": "uuid-x",
            "language": "pt_BR",
            "country": "Brasil",
            "body": {"type": "BODY", "text": "Hello"},
            "footer": {"type": "FOOTER", "text": "Bye"},
            "buttons": [
                {"button_type": "URL", "url": "https://x", "text": "Open"},
            ],
        }

        # Act
        result = serializer.create(validated)

        # Assert service call with assembled components
        mock_template_service_cls.assert_called_once()
        svc_instance.create_template_message.assert_called_once()
        call_kwargs = svc_instance.create_template_message.call_args.kwargs
        self.assertEqual(call_kwargs["waba_id"], "waba-xyz")
        self.assertEqual(call_kwargs["name"], "t-name")
        self.assertEqual(call_kwargs["category"], "UTILITY")
        self.assertEqual(call_kwargs["language"], "pt_BR")
        # Components must include body, footer and a BUTTONS block
        components = call_kwargs["components"]
        self.assertEqual(components[0]["type"], "BODY")
        self.assertEqual(components[1]["type"], "FOOTER")
        self.assertEqual(components[2]["type"], "BUTTONS")
        self.assertEqual(components[2]["buttons"][0]["type"], "URL")

        # Persistence calls
        mock_template_translation.objects.create.assert_called_once()
        self.assertIs(result, translation_obj)
        # Buttons saved
        mock_template_button.objects.create.assert_called_once()
        # Header not saved since it wasn't provided
        mock_template_header.objects.create.assert_not_called()

    @patch("marketplace.wpp_templates.serializers.extract_body_example")
    @patch("marketplace.wpp_templates.serializers.PhotoAPIService")
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_create_with_media_header_and_phone_button(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
        mock_photo_api_service_cls,
        mock_extract_body_example,
    ):
        """Covers media header upload flow and phone button formatting, plus body example extraction."""
        # Arrange template and service
        template_instance = MagicMock()
        template_instance.name = "media-tpl"
        template_instance.category = "MARKETING"
        template_instance.app.config = {"waba": {"id": "waba-from-nested"}}
        template_instance.app.apptype.get_access_token.return_value = "acc-2"
        mock_template_message.objects.get.return_value = template_instance

        svc_instance = MagicMock()
        svc_instance.create_template_message.return_value = {"id": "mid-2"}
        mock_template_service_cls.return_value = svc_instance

        mock_extract_body_example.return_value = ["ex1", "ex2"]

        # Photo API mocks
        photo_api_instance = MagicMock()
        photo_api_instance.create_upload_session.return_value = "session-1"
        photo_api_instance.upload_session.return_value = {"h": "handle-xyz"}
        mock_photo_api_service_cls.return_value = photo_api_instance

        serializer = TemplateTranslationSerializer()
        validated = {
            "template_uuid": "uuid-y",
            "language": "en_US",
            "country": "US",
            "body": {"type": "BODY", "text": "Text", "example": {"body_text": ["a"]}},
            "header": {
                "header_type": "IMAGE",
                "text": "Header",
                # Minimal valid data URI for test: 'hello' base64
                "example": "data:image/png;base64,aGVsbG8=",
            },
            "footer": {"type": "FOOTER", "text": "Footer"},
            "buttons": [
                {
                    "button_type": "PHONE_NUMBER",
                    "country_code": "55",
                    "phone_number": "999999999",
                    "text": "Call",
                }
            ],
        }

        translation_obj = MagicMock()
        mock_template_translation.objects.create.return_value = translation_obj

        result = serializer.create(validated)

        # Ensure WABA id is selected from nested config path
        svc_instance.create_template_message.assert_called_once()
        self.assertEqual(
            svc_instance.create_template_message.call_args.kwargs["waba_id"],
            "waba-from-nested",
        )

        # Components include transformed header with upload handle and phone formatting
        comps = svc_instance.create_template_message.call_args.kwargs["components"]
        # Body, Header, Footer, Buttons blocks present
        self.assertEqual([c["type"] for c in comps[:3]], ["BODY", "HEADER", "FOOTER"])
        header_comp = comps[1]
        self.assertEqual(header_comp["format"], "IMAGE")
        self.assertEqual(header_comp["example"], {"header_handle": "handle-xyz"})

        buttons_block = [c for c in comps if c["type"] == "BUTTONS"][0]
        btn = buttons_block["buttons"][0]
        self.assertEqual(btn["type"], "PHONE_NUMBER")
        self.assertEqual(btn["phone_number"], "+55 999999999")
        self.assertNotIn("country_code", btn)

        # Body example extraction used in persistence
        mock_template_translation.objects.create.assert_called_once()
        kwargs = mock_template_translation.objects.create.call_args.kwargs
        self.assertEqual(kwargs["body_example"], ["ex1", "ex2"])

        self.assertIs(result, translation_obj)
        # TemplateHeader saved (without original example)
        mock_template_header.objects.create.assert_called_once()

    def test_to_representation_adds_header(self):
        """to_representation must include header dict when present on instance."""
        instance = MagicMock()
        header_obj = MagicMock()
        header_obj.to_dict.return_value = {"type": "HEADER", "format": "TEXT"}
        instance.headers.first.return_value = header_obj

        serializer = TemplateTranslationSerializer()
        data = serializer.to_representation(instance)

        self.assertEqual(data["header"], {"type": "HEADER", "format": "TEXT"})


class TestTemplateMessageSerializer(TestCase):
    """Unit tests for TemplateMessageSerializer create() and to_representation()."""

    def test_to_representation_text_preview(self):
        """Ensure text_preview is populated from first translation body when available."""
        instance = MagicMock()
        translation = MagicMock()
        translation.body = "Hello"
        instance.translations.first.return_value = translation

        serializer = TemplateMessageSerializer()
        out = serializer.to_representation(instance)
        self.assertEqual(out["text_preview"], "Hello")

    @patch("marketplace.wpp_templates.serializers.User")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    @patch("marketplace.wpp_templates.serializers.App")
    def test_create_success(self, mock_app, mock_template_message_cls, mock_user):
        """Create should validate, save and return the TemplateMessage instance."""
        app_obj = MagicMock()
        mock_app.objects.get.return_value = app_obj

        tm_instance = MagicMock()
        mock_template_message_cls.return_value = tm_instance

        admin_user = MagicMock()
        admin_user.id = 7
        mock_user.objects.get_admin_user.return_value = admin_user

        serializer = TemplateMessageSerializer()
        payload = {
            "name": "welcome",
            "category": "UTILITY",
            "app_uuid": "app-1",
            "gallery_version": None,
        }

        out = serializer.create(payload)

        mock_template_message_cls.assert_called_once()
        tm_instance.full_clean.assert_called_once()
        tm_instance.save.assert_called_once()
        self.assertIs(out, tm_instance)

    @patch("marketplace.wpp_templates.serializers.User")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    @patch("marketplace.wpp_templates.serializers.App")
    def test_create_validation_error_translated(
        self, mock_app, mock_template_message_cls, mock_user
    ):
        """Create should translate Django ValidationError to DRF ValidationError."""
        app_obj = MagicMock()
        mock_app.objects.get.return_value = app_obj

        tm_instance = MagicMock()
        tm_instance.full_clean.side_effect = DjangoValidationError(
            {"name": ["invalid"]}
        )
        mock_template_message_cls.return_value = tm_instance

        admin_user = MagicMock()
        admin_user.id = 1
        mock_user.objects.get_admin_user.return_value = admin_user

        serializer = TemplateMessageSerializer()
        payload = {
            "name": "welcome",
            "category": "UTILITY",
            "app_uuid": "app-1",
        }

        with self.assertRaises(drf_serializers.ValidationError):
            serializer.create(payload)
