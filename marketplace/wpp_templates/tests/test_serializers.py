from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase, override_settings
from rest_framework import serializers as drf_serializers
from rest_framework.exceptions import APIException

from marketplace.clients.exceptions import CustomAPIException
from marketplace.wpp_templates.parameters import PARAMETER_FORMAT_NAMED
from marketplace.wpp_templates.serializers import (
    TemplateMessageSerializer,
    TemplateTranslationSerializer,
)

THREE_NAME_BODY = "Olá {{nome}}, sua cota {{cota}} vence em {{data}}"
THREE_NAME_EXAMPLES = [
    {"param_name": "nome", "example": "João"},
    {"param_name": "cota", "example": "3/12"},
    {"param_name": "data", "example": "20/10/2026"},
]
POSITIONAL_BODY = "Olá {{1}}, seu pedido {{2}} foi enviado."


def _translation_payload(text, examples=None, language="pt_BR"):
    body = {"type": "BODY", "text": text}
    if examples is not None:
        body["example"] = {"body_text_named_params": examples}
    return {
        "template_uuid": "uuid-named",
        "language": language,
        "body": body,
    }


def _body_error_text(serializer):
    errors = serializer.errors["body"]
    if isinstance(errors, list):
        return " ".join(str(item) for item in errors)
    return str(errors)


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


class TestNamedTemplateAuthoring(TestCase):
    """Story 3: named authoring accept, reject matrix, flag and positional parity."""

    def _stub_create_path(
        self,
        mock_template_message,
        mock_template_service_cls,
        mock_template_translation,
        create_side_effect=None,
    ):
        template_instance = MagicMock()
        template_instance.name = "order_update"
        template_instance.category = "UTILITY"
        template_instance.app.config = {"wa_waba_id": "waba-xyz"}
        template_instance.app.apptype.get_access_token.return_value = "acc-1"
        mock_template_message.objects.get.return_value = template_instance

        svc_instance = MagicMock()
        if create_side_effect is not None:
            svc_instance.create_template_message.side_effect = create_side_effect
        else:
            svc_instance.create_template_message.return_value = {"id": "mid-named"}
        mock_template_service_cls.return_value = svc_instance

        translation_obj = MagicMock()
        mock_template_translation.objects.create.return_value = translation_obj
        return svc_instance

    def _assert_rejected_without_meta(
        self, serializer, mock_template_service_cls, mock_template_translation
    ):
        self.assertFalse(serializer.is_valid())
        self.assertIn("body", serializer.errors)
        mock_template_service_cls.return_value.create_template_message.assert_not_called()
        mock_template_translation.objects.create.assert_not_called()

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_named_body_submits_named_payload_and_records_parameters(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        svc_instance = self._stub_create_path(
            mock_template_message,
            mock_template_service_cls,
            mock_template_translation,
        )
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(THREE_NAME_BODY, THREE_NAME_EXAMPLES)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        svc_instance.create_template_message.assert_called_once()
        call_kwargs = svc_instance.create_template_message.call_args.kwargs
        self.assertEqual(call_kwargs["parameter_format"], "named")
        body_component = call_kwargs["components"][0]
        named_examples = body_component["example"]["body_text_named_params"]
        self.assertEqual(
            [entry["param_name"] for entry in named_examples],
            ["nome", "cota", "data"],
        )
        self.assertEqual(
            named_examples,
            [
                {"param_name": "nome", "example": "João"},
                {"param_name": "cota", "example": "3/12"},
                {"param_name": "data", "example": "20/10/2026"},
            ],
        )

        create_kwargs = mock_template_translation.objects.create.call_args.kwargs
        self.assertEqual(create_kwargs["parameter_format"], PARAMETER_FORMAT_NAMED)
        self.assertEqual(create_kwargs["variable_count"], 3)
        self.assertEqual(create_kwargs["body_named_params"], named_examples)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_rejects_mixed_named_and_positional_body(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload("Olá {{nome}}, pedido {{1}}")
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("one parameter format", error.lower())
        self.assertIn("nome", error)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_rejects_duplicated_parameter_name(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(
                "Olá {{nome}}, tudo bem {{nome}}?",
                [{"param_name": "nome", "example": "João"}],
            )
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("nome", error)
        self.assertIn("duplicated", error.lower())

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_rejects_uppercase_parameter_name(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(
                "Olá {{Nome}}", [{"param_name": "Nome", "example": "João"}]
            )
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("Nome", error)
        self.assertIn("^[a-z_][a-z0-9_]*$", error)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_rejects_leading_digit_parameter_name(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(
                "Seu código {{2fa_code}}",
                [{"param_name": "2fa_code", "example": "123456"}],
            )
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("2fa_code", error)
        self.assertIn("^[a-z_][a-z0-9_]*$", error)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_rejects_named_parameter_without_example(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload("Olá {{nome}}")
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("nome", error)
        self.assertIn("example", error.lower())

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_surfaces_meta_body_rejection_verbatim_without_local_record(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        meta_reason = "Meta rejected body parameter 'nome' because example is too long"
        self._stub_create_path(
            mock_template_message,
            mock_template_service_cls,
            mock_template_translation,
            create_side_effect=CustomAPIException(detail=meta_reason, status_code=400),
        )
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(THREE_NAME_BODY, THREE_NAME_EXAMPLES)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(drf_serializers.ValidationError) as ctx:
            serializer.save()
        self.assertIn("body", ctx.exception.detail)
        self.assertIn(meta_reason, str(ctx.exception.detail["body"]))
        mock_template_translation.objects.create.assert_not_called()

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_unsupported_parameter_format_is_configuration_error(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        self._stub_create_path(
            mock_template_message,
            mock_template_service_cls,
            mock_template_translation,
            create_side_effect=CustomAPIException(
                detail={
                    "error": {"message": "(#100) parameter_format is not a valid field"}
                },
                status_code=400,
            ),
        )
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(THREE_NAME_BODY, THREE_NAME_EXAMPLES)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with self.assertRaises(APIException) as ctx:
            serializer.save()
        self.assertNotIsInstance(ctx.exception, drf_serializers.ValidationError)
        message = str(ctx.exception.detail).lower()
        self.assertIn("parameter_format", message)
        self.assertIn("does not support", message)
        self.assertIn("capability", message)
        mock_template_translation.objects.create.assert_not_called()

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=False)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_flag_off_rejects_named_body_without_downgrade(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(THREE_NAME_BODY, THREE_NAME_EXAMPLES)
        )
        self._assert_rejected_without_meta(
            serializer, mock_template_service_cls, mock_template_translation
        )
        error = _body_error_text(serializer)
        self.assertIn("not enabled", error.lower())
        self.assertNotIn("positional", error.lower())

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    def test_flag_on_permits_named_body(
        self, mock_template_service_cls, mock_template_translation
    ):
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(THREE_NAME_BODY, THREE_NAME_EXAMPLES)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=False)
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_positional_create_omits_parameter_format_when_flag_off(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        svc_instance = self._stub_create_path(
            mock_template_message,
            mock_template_service_cls,
            mock_template_translation,
        )
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(POSITIONAL_BODY)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        call_kwargs = svc_instance.create_template_message.call_args.kwargs
        self.assertNotIn("parameter_format", call_kwargs)
        create_kwargs = mock_template_translation.objects.create.call_args.kwargs
        self.assertEqual(create_kwargs["variable_count"], 0)
        self.assertNotIn("parameter_format", create_kwargs)

    @override_settings(WHATSAPP_NAMED_TEMPLATES_ENABLED=True)
    @patch("marketplace.wpp_templates.serializers.TemplateHeader")
    @patch("marketplace.wpp_templates.serializers.TemplateButton")
    @patch("marketplace.wpp_templates.serializers.TemplateTranslation")
    @patch("marketplace.wpp_templates.serializers.TemplateService")
    @patch("marketplace.wpp_templates.serializers.FacebookClient")
    @patch("marketplace.wpp_templates.serializers.TemplateMessage")
    def test_positional_create_omits_parameter_format_when_flag_on(
        self,
        mock_template_message,
        mock_facebook_client,
        mock_template_service_cls,
        mock_template_translation,
        mock_template_button,
        mock_template_header,
    ):
        svc_instance = self._stub_create_path(
            mock_template_message,
            mock_template_service_cls,
            mock_template_translation,
        )
        serializer = TemplateTranslationSerializer(
            data=_translation_payload(POSITIONAL_BODY)
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        call_kwargs = svc_instance.create_template_message.call_args.kwargs
        self.assertNotIn("parameter_format", call_kwargs)
