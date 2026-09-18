import logging
import uuid
from datetime import timezone
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.utils import timezone as django_timezone

from marketplace.applications.models import App
from marketplace.core.pacing.constants import TTL_WHATSAPP_TEMPLATES
from marketplace.wpp_templates.models import (
    PARAMETER_FORMAT_NAMED,
    PARAMETER_FORMAT_POSITIONAL,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.usecases.template_sync import (
    TemplateSyncCooldownError,
    TemplateSyncDisabledError,
    TemplateSyncFailedError,
    TemplateSyncUseCase,
)

User = get_user_model()

NAMED_BODY = "Olá {{nome}}, sua cota {{cota}}"
NAMED_BODY_WITH_DUE_DATE = "Olá {{nome}}, sua cota {{cota}} vence hoje"
POSITIONAL_BODY = "Olá {{1}}, seu pedido {{2}} foi enviado."
NAMED_EXAMPLE_NOME = "João"
NAMED_EXAMPLE_COTA = "3/12"
POSITIONAL_EXAMPLE_ORDER = "12345"


def _named_examples(*pairs):
    return [{"param_name": name, "example": example} for name, example in pairs]


def _meta_template(
    template_id,
    name,
    body,
    example=None,
    parameter_format=None,
    omit_format=False,
    language="pt_BR",
    status="APPROVED",
    category="UTILITY",
):
    body_component = {"type": "BODY", "text": body}
    if example is not None:
        body_component["example"] = example
    template = {
        "id": template_id,
        "name": name,
        "language": language,
        "status": status,
        "category": category,
        "components": [body_component],
    }
    if not omit_format:
        template["parameter_format"] = parameter_format
    return template


def _named_meta_template(
    template_id="1001",
    name="cota_aviso",
    parameter_format="named",
    body=NAMED_BODY_WITH_DUE_DATE,
    examples=None,
):
    if examples is None:
        examples = _named_examples(
            ("nome", NAMED_EXAMPLE_NOME),
            ("cota", NAMED_EXAMPLE_COTA),
        )
    return _meta_template(
        template_id=template_id,
        name=name,
        body=body,
        example={"body_text_named_params": examples},
        parameter_format=parameter_format,
    )


def _positional_meta_template(
    template_id="1002",
    name="pedido_enviado",
    omit_format=True,
    parameter_format=None,
):
    return _meta_template(
        template_id=template_id,
        name=name,
        body=POSITIONAL_BODY,
        example={"body_text": [[NAMED_EXAMPLE_NOME, POSITIONAL_EXAMPLE_ORDER]]},
        parameter_format=parameter_format,
        omit_format=omit_format,
    )


class TestTemplateSyncUseCase(SimpleTestCase):
    """Unit tests for TemplateSyncUseCase using dependency injection and instance-level mocks."""

    def _make_app(self, with_waba: bool = False):
        app = MagicMock()
        app.uuid = "app-uuid-1"
        app.flow_object_uuid = "flow-uuid-1"
        app.apptype.get_access_token.return_value = "access-token"
        app.config = (
            {"waba": {"id": "waba-in-config"}}
            if with_waba
            else {"wa_waba_id": "waba-direct"}
        )
        return app

    def test_init_access_token_error(self):
        """__init__ should log and raise when get_access_token raises ValueError."""
        app = MagicMock()
        app.uuid = "app-uuid-err"
        app.apptype.get_access_token.side_effect = ValueError("bad token")
        with self.assertRaises(ValueError):
            TemplateSyncUseCase(app)

    def test_sync_templates_error_from_service(self):
        """When Meta service returns error, handle_error_and_update_config is called and returns early."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        # Replace external services with mocks
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()
        uc.template_service.list_template_messages.return_value = {"error": {"code": 1}}

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.handle_error_and_update_config"
        ) as mock_handle:
            result = uc.sync_templates()
            mock_handle.assert_called_once()
            uc.flows_client.update_facebook_templates.assert_not_called()
            self.assertFalse(result)
            self.assertNotIn("templates_last_synced_at", app.config)

    def test_sync_templates_success_existing_translation(self):
        """Successful sync with existing translation and all component types present."""
        app = self._make_app(with_waba=False)
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payload = {
            "id": "tpl-1",
            "name": "welcome",
            "category": "UTILITY",
            "language": "en_US",
            "status": "APPROVED",
            "components": [
                {"type": "BODY", "text": "Hello", "example": {"body_text": ["a", "b"]}},
                {"type": "FOOTER", "text": "Bye"},
                {
                    "type": "HEADER",
                    "format": "TEXT",
                    "text": "Header",
                    "example": {"header_handle": "hdr-1"},
                },
                {
                    "type": "BUTTONS",
                    "buttons": [
                        {"type": "URL", "text": "Open", "url": "https://x"},
                        {
                            "type": "PHONE_NUMBER",
                            "text": "Call",
                            "phone_number": "+55 9",
                        },
                    ],
                },
            ],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.extract_body_example",
            return_value=["a", "b"],
        ) as mock_extract, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ), patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateHeader"
        ) as mock_header, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateButton"
        ) as mock_button:
            # Configure get_or_create tuples
            mock_header.objects.get_or_create.return_value = (MagicMock(), True)
            mock_button.objects.get_or_create.return_value = (MagicMock(), True)
            # Existing translation branch
            existing_translation = MagicMock()
            found_template = MagicMock()
            existing_translation.template = found_template
            mock_qs = MagicMock()
            mock_qs.__bool__.return_value = True
            mock_qs.last.return_value = existing_translation
            mock_translation.objects.filter.return_value = mock_qs

            returned_translation = MagicMock()
            mock_translation.objects.get_or_create.return_value = (
                returned_translation,
                True,
            )

            result = uc.sync_templates()

            uc.flows_client.update_facebook_templates.assert_called_once()
            self.assertTrue(result)
            self.assertIn("templates_last_synced_at", app.config)
            app.save.assert_called()
            mock_extract.assert_called_once()
            # Header created
            mock_header.objects.get_or_create.assert_called()
            # Buttons created
            self.assertGreaterEqual(mock_button.objects.get_or_create.call_count, 1)
            # Translation saved
            returned_translation.save.assert_called_once()

    def test_sync_templates_success_no_existing_translation(self):
        """Successful sync creating new TemplateMessage when no translation exists."""
        app = self._make_app(with_waba=True)
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payload = {
            "id": "tpl-2",
            "name": "promo",
            "category": "MARKETING",
            "language": "es",
            "status": "PENDING",
            "components": [{"type": "BODY", "text": "Hola"}],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message:
            mock_translation.objects.filter.return_value = []
            tmpl = MagicMock()
            mock_message.objects.get_or_create.return_value = (tmpl, True)
            returned_translation = MagicMock()
            mock_translation.objects.get_or_create.return_value = (
                returned_translation,
                True,
            )

            uc.sync_templates()

            mock_message.objects.get_or_create.assert_called_once()
            returned_translation.save.assert_called_once()

    def test_sync_templates_flows_update_raises_but_continues(self):
        """Flows update exception should be logged but processing continues."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()
        uc.flows_client.update_facebook_templates.side_effect = Exception("boom")

        template_payload = {
            "id": "tpl-3",
            "name": "sale",
            "category": "UTILITY",
            "language": "en",
            "status": "APPROVED",
            "components": [],
        }
        uc.template_service.list_template_messages.return_value = {
            "data": [template_payload]
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            mock_translation.objects.filter.return_value = []
        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation2:
            mock_message.objects.get_or_create.return_value = (MagicMock(), True)
            mock_translation2.objects.filter.return_value = []
            mock_translation2.objects.get_or_create.return_value = (MagicMock(), True)

            uc.sync_templates()  # Should not raise
            mock_translation2.objects.get_or_create.assert_called_once()

    def test_sync_templates_per_item_exception_continue(self):
        """Exceptions inside per-template loop should be caught and continue."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        template_payloads = [
            {
                "id": "tpl-bad",
                "name": "bad",
                "category": "U",
                "language": "en",
                "status": "A",
                "components": [],
            },
            {
                "id": "tpl-ok",
                "name": "ok",
                "category": "U",
                "language": "en",
                "status": "A",
                "components": [],
            },
        ]
        uc.template_service.list_template_messages.return_value = {
            "data": template_payloads
        }

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            mock_message.objects.get_or_create.return_value = (MagicMock(), True)
            # First raises, second passes
            mock_translation.objects.filter.return_value = []
            mock_translation.objects.get_or_create.side_effect = [
                Exception("item error"),
                (MagicMock(), True),
            ]

            uc.sync_templates()  # Should not raise
            self.assertEqual(mock_translation.objects.get_or_create.call_count, 2)

    def test_sync_templates_reuses_prefetched_templates(self):
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation, patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateMessage"
        ) as mock_message:
            mock_translation.objects.filter.return_value = []
            mock_message.objects.get_or_create.return_value = (MagicMock(), True)
            mock_translation.objects.get_or_create.return_value = (MagicMock(), True)

            uc.sync_templates(
                templates=[{"id": "tpl-1", "name": "n", "components": []}]
            )

            uc.template_service.list_template_messages.assert_not_called()
            mock_message.objects.get_or_create.assert_called_once()

    def test_delete_unexistent_translations(self):
        """Covers cleanup logic for missing translations and templates."""
        app = self._make_app()
        uc = TemplateSyncUseCase(app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()

        # Prepare app templates
        t1 = MagicMock()
        t1.name = "t1"
        t1.translations.all().count.return_value = 1
        t2 = MagicMock()
        t2.name = "t2"
        t2.translations.all().count.return_value = 0  # Trigger delete if reached
        app.templates.all.return_value = [t1, t2]

        templates = [{"id": "keep"}]  # Only 'keep' remains on remote
        with patch(
            "marketplace.wpp_templates.usecases.template_sync.TemplateTranslation"
        ) as mock_translation:
            # For t1: no translations -> delete and continue
            mock_translation.objects.filter.side_effect = [
                [],  # For t1, falsy -> delete
                [
                    MagicMock(message_template_id="remove")
                ],  # For t2, 1 translation to delete
            ]

            uc._delete_unexistent_translations(templates)

            # t1 should be deleted due to no translations
            t1.delete.assert_called_once()
            # t2's translation should be deleted (not in 'keep')
            # We can't access the exact translation mock easily due to side_effect,
            # but ensure filter was called twice and t2 was also deleted after count==0
            self.assertEqual(mock_translation.objects.filter.call_count, 2)
            t2.delete.assert_called_once()


class TestTemplateSyncRequestSync(SimpleTestCase):
    def _make_app(self, config=None):
        app = MagicMock()
        app.uuid = "app-uuid-1"
        app.config = config if config is not None else {}
        app.apptype.get_access_token.return_value = "access-token"
        return app

    def test_get_sync_status_without_previous_sync(self):
        app = self._make_app()
        self.assertEqual(
            TemplateSyncUseCase.get_sync_status(app),
            {"last_synced_at": None},
        )

    def test_request_sync_disabled(self):
        app = self._make_app(config={"ignores_meta_sync": {"code": 100}})
        with self.assertRaises(TemplateSyncDisabledError):
            TemplateSyncUseCase.request_sync(app)

    def test_request_sync_within_cooldown(self):
        last_synced_at = django_timezone.now().isoformat()
        app = self._make_app(config={"templates_last_synced_at": last_synced_at})
        with self.assertRaises(TemplateSyncCooldownError) as raised:
            TemplateSyncUseCase.request_sync(app)
        payload = raised.exception.to_dict()
        self.assertEqual(payload["last_synced_at"], last_synced_at)
        self.assertGreaterEqual(payload["retry_after_seconds"], 1)

    def test_parse_invalid_and_naive_timestamps(self):
        self.assertIsNone(TemplateSyncUseCase._parse_last_synced_at(None))
        self.assertIsNone(TemplateSyncUseCase._parse_last_synced_at("not-a-date"))
        parsed = TemplateSyncUseCase._parse_last_synced_at("2026-08-20T15:00:00")
        self.assertEqual(parsed.tzinfo, timezone.utc)

    @patch.object(TemplateSyncUseCase, "sync_templates", return_value=True)
    def test_request_sync_success(self, mock_sync_templates):
        last_synced_at = "2026-08-20T15:00:00+00:00"
        app = self._make_app()

        def refresh():
            app.config["templates_last_synced_at"] = last_synced_at

        app.refresh_from_db.side_effect = refresh

        result = TemplateSyncUseCase.request_sync(app)

        mock_sync_templates.assert_called_once_with()
        self.assertEqual(result, {"last_synced_at": last_synced_at})

    @patch.object(TemplateSyncUseCase, "sync_templates", return_value=False)
    def test_request_sync_meta_failure(self, mock_sync_templates):
        app = self._make_app()
        with self.assertRaises(TemplateSyncFailedError):
            TemplateSyncUseCase.request_sync(app)
        mock_sync_templates.assert_called_once_with()

    def test_request_sync_invalid_timestamp_skips_cooldown(self):
        app = self._make_app(config={"templates_last_synced_at": "invalid"})
        with patch.object(
            TemplateSyncUseCase, "sync_templates", return_value=True
        ) as mock_sync:
            app.refresh_from_db.side_effect = lambda: None
            TemplateSyncUseCase.request_sync(app)
            mock_sync.assert_called_once_with()

    def test_cooldown_error_payload(self):
        error = TemplateSyncCooldownError(retry_after_seconds=12, last_synced_at="ts")
        self.assertEqual(
            error.to_dict(),
            {
                "error": "Templates were synced less than 1 hour ago",
                "last_synced_at": "ts",
                "retry_after_seconds": 12,
            },
        )


class TemplateSyncRecordingTestCase(TestCase):
    def setUp(self):
        self.app = self._create_app()

    def _create_app(self, waba_id="waba-shared"):
        return App.objects.create(
            config={
                "wa_waba_id": waba_id,
                "wa_user_token": "test-token",
            },
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wpp-cloud",
            created_by=User.objects.get_admin_user(),
            flow_object_uuid=uuid.uuid4(),
        )

    def _use_case(self, app=None):
        uc = TemplateSyncUseCase(app or self.app)
        uc.template_service = MagicMock()
        uc.flows_client = MagicMock()
        return uc

    def _sync(self, templates, app=None, use_case=None):
        uc = use_case or self._use_case(app)
        with self.assertLogs(
            "marketplace.wpp_templates.usecases.template_sync", level="INFO"
        ) as captured:
            result = uc.sync_templates(templates=templates)
        return uc, captured, result

    def _translation(self, name, app=None):
        return TemplateTranslation.objects.get(
            template__app=app or self.app, template__name=name
        )

    def _assert_no_example_values(self, captured, *values):
        for record in captured.records:
            message = record.getMessage()
            for value in values:
                self.assertNotIn(
                    value,
                    message,
                    msg=(
                        f"example value {value!r} leaked at "
                        f"{record.levelname}: {message}"
                    ),
                )

    def test_independent_test_named_and_positional_in_one_meta_list(self):
        self.assertFalse(settings.WHATSAPP_NAMED_TEMPLATES_ENABLED)
        named = _named_meta_template()
        positional = _positional_meta_template()
        meta_templates = [named, positional]

        uc, captured, result = self._sync(meta_templates)

        self.assertTrue(result)
        named_translation = self._translation("cota_aviso")
        self.assertEqual(named_translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            [entry["param_name"] for entry in named_translation.body_named_params],
            ["nome", "cota"],
        )
        self.assertEqual(
            named_translation.body_named_params,
            [
                {"param_name": "nome", "example": NAMED_EXAMPLE_NOME},
                {"param_name": "cota", "example": NAMED_EXAMPLE_COTA},
            ],
        )
        self.assertEqual(named_translation.variable_count, 2)
        self.assertIsNone(named_translation.parameter_anomaly)

        positional_translation = self._translation("pedido_enviado")
        self.assertEqual(
            positional_translation.parameter_format, PARAMETER_FORMAT_POSITIONAL
        )
        self.assertEqual(positional_translation.body_named_params, [])
        self.assertEqual(positional_translation.variable_count, 0)
        self.assertEqual(
            positional_translation.body_example,
            [NAMED_EXAMPLE_NOME, POSITIONAL_EXAMPLE_ORDER],
        )
        self.assertIsNone(positional_translation.parameter_anomaly)

        self.assertIs(
            uc.flows_client.update_facebook_templates.call_args.args[1],
            meta_templates,
        )
        self._assert_no_example_values(
            captured,
            NAMED_EXAMPLE_NOME,
            NAMED_EXAMPLE_COTA,
            POSITIONAL_EXAMPLE_ORDER,
        )

    def test_bulk_push_forwards_meta_list_by_identity(self):
        meta_templates = [_named_meta_template(), _positional_meta_template()]
        uc, _, _ = self._sync(meta_templates)
        self.assertIs(
            uc.flows_client.update_facebook_templates.call_args.args[1],
            meta_templates,
        )

    def test_absent_parameter_format_records_positional(self):
        _, captured, _ = self._sync(
            [_meta_template("2001", "no_format", POSITIONAL_BODY, omit_format=True)]
        )
        translation = self._translation("no_format")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(translation.body_named_params, [])
        self.assertEqual(translation.variable_count, 0)
        self.assertIsNone(translation.parameter_anomaly)
        self._assert_no_example_values(
            captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA, POSITIONAL_EXAMPLE_ORDER
        )

    def test_named_casings_both_record_named(self):
        cases = (("named", "lower_named"), ("NAMED", "upper_named"))
        templates = [
            _named_meta_template(
                template_id=str(index),
                name=name,
                parameter_format=raw,
            )
            for index, (raw, name) in enumerate(cases, start=3001)
        ]
        _, captured, _ = self._sync(templates)
        for _, name in cases:
            translation = self._translation(name)
            self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
            self.assertEqual(translation.variable_count, 2)
            self.assertIsNone(translation.parameter_anomaly)
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_unrecognised_format_records_positional_without_inspecting_body(self):
        template = _meta_template(
            "4001",
            "unrecognised",
            NAMED_BODY,
            example={
                "body_text_named_params": _named_examples(
                    ("nome", NAMED_EXAMPLE_NOME),
                    ("cota", NAMED_EXAMPLE_COTA),
                )
            },
            parameter_format="SOMETHING_ELSE",
        )
        _, captured, _ = self._sync([template])
        translation = self._translation("unrecognised")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(translation.body_named_params, [])
        self.assertEqual(translation.variable_count, 0)
        self.assertEqual(translation.parameter_anomaly["type"], "UNRECOGNISED_FORMAT")
        self.assertEqual(
            translation.parameter_anomaly["reported_format"], "SOMETHING_ELSE"
        )
        warning_messages = [
            record.getMessage()
            for record in captured.records
            if record.levelno == logging.WARNING
        ]
        self.assertTrue(warning_messages)
        warning = warning_messages[0]
        self.assertIn("UNRECOGNISED_FORMAT", warning)
        self.assertIn(str(self.app.uuid), warning)
        self.assertIn(str(self.app.project_uuid), warning)
        self.assertIn("unrecognised", warning)
        self.assertIn("4001", warning)
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_named_body_with_zero_placeholders_records_empty_names(self):
        _, captured, _ = self._sync(
            [
                _meta_template(
                    "5001",
                    "named_plain",
                    "Olá, tudo bem?",
                    parameter_format="NAMED",
                )
            ]
        )
        translation = self._translation("named_plain")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(translation.body_named_params, [])
        self.assertEqual(translation.variable_count, 0)
        self.assertIsNone(translation.parameter_anomaly)
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_body_example_name_mismatch_keeps_body_names_and_both_sets(self):
        _, captured, _ = self._sync(
            [
                _named_meta_template(
                    template_id="6001",
                    name="mismatch",
                    parameter_format="NAMED",
                    body=NAMED_BODY,
                    examples=_named_examples(
                        ("nome", NAMED_EXAMPLE_NOME),
                        ("quota", NAMED_EXAMPLE_COTA),
                    ),
                )
            ]
        )
        translation = self._translation("mismatch")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            translation.body_named_params,
            [
                {"param_name": "nome", "example": NAMED_EXAMPLE_NOME},
                {"param_name": "cota", "example": None},
            ],
        )
        self.assertEqual(translation.variable_count, 2)
        self.assertEqual(
            translation.parameter_anomaly["type"], "BODY_EXAMPLE_NAME_MISMATCH"
        )
        self.assertEqual(
            translation.parameter_anomaly["body_param_names"], ["nome", "cota"]
        )
        self.assertEqual(
            translation.parameter_anomaly["example_param_names"], ["nome", "quota"]
        )
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_missing_named_example_stores_null(self):
        _, captured, _ = self._sync(
            [
                _named_meta_template(
                    template_id="7001",
                    name="missing_example",
                    parameter_format="NAMED",
                    body="Olá {{nome}}",
                    examples=_named_examples(("nome", "")),
                )
            ]
        )
        translation = self._translation("missing_example")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            translation.body_named_params,
            [{"param_name": "nome", "example": None}],
        )
        self.assertEqual(translation.parameter_anomaly["type"], "MISSING_NAMED_EXAMPLE")
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_duplicate_body_param_name_is_not_deduplicated(self):
        _, captured, _ = self._sync(
            [
                _named_meta_template(
                    template_id="8001",
                    name="duplicate_name",
                    parameter_format="NAMED",
                    body="Olá {{nome}}, tudo bem {{nome}}?",
                    examples=_named_examples(("nome", NAMED_EXAMPLE_NOME)),
                )
            ]
        )
        translation = self._translation("duplicate_name")
        self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            translation.body_named_params,
            [
                {"param_name": "nome", "example": NAMED_EXAMPLE_NOME},
                {"param_name": "nome", "example": NAMED_EXAMPLE_NOME},
            ],
        )
        self.assertEqual(translation.variable_count, 2)
        self.assertEqual(
            translation.parameter_anomaly["type"], "DUPLICATE_BODY_PARAM_NAME"
        )
        self.assertEqual(
            translation.parameter_anomaly["body_param_names"], ["nome", "nome"]
        )
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_positional_or_omitted_format_with_named_body_does_not_infer_named(self):
        templates = [
            _meta_template(
                "9001",
                "positional_named_body",
                NAMED_BODY,
                parameter_format="positional",
            ),
            _meta_template(
                "9002",
                "omitted_named_body",
                NAMED_BODY,
                omit_format=True,
            ),
        ]
        _, captured, _ = self._sync(templates)
        for name in ("positional_named_body", "omitted_named_body"):
            translation = self._translation(name)
            self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_POSITIONAL)
            self.assertEqual(translation.body_named_params, [])
            self.assertEqual(translation.variable_count, 0)
            self.assertEqual(
                translation.parameter_anomaly["type"], "POSITIONAL_FORMAT_NAMED_BODY"
            )
            self.assertEqual(
                translation.parameter_anomaly["body_param_names"], ["nome", "cota"]
            )
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_changed_names_at_meta_are_replaced_in_place(self):
        first = _named_meta_template(template_id="1101", name="renamed_params")
        self._sync([first])
        original_template_id = TemplateMessage.objects.get(
            app=self.app, name="renamed_params"
        ).pk
        original_translation_id = self._translation("renamed_params").pk

        updated = _named_meta_template(
            template_id="1101",
            name="renamed_params",
            parameter_format="NAMED",
            body="Olá {{nome}}, seu valor {{valor}}",
            examples=_named_examples(
                ("nome", NAMED_EXAMPLE_NOME),
                ("valor", NAMED_EXAMPLE_COTA),
            ),
        )
        _, captured, _ = self._sync([updated])

        self.assertEqual(TemplateMessage.objects.filter(app=self.app).count(), 1)
        self.assertEqual(
            TemplateTranslation.objects.filter(template__app=self.app).count(), 1
        )
        self.assertEqual(
            TemplateMessage.objects.get(app=self.app, name="renamed_params").pk,
            original_template_id,
        )
        translation = self._translation("renamed_params")
        self.assertEqual(translation.pk, original_translation_id)
        self.assertEqual(
            [entry["param_name"] for entry in translation.body_named_params],
            ["nome", "valor"],
        )
        self.assertEqual(translation.variable_count, 2)
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_shared_waba_records_the_same_values_without_touching_pacing(self):
        other_app = self._create_app()
        meta_templates = [_named_meta_template()]
        budget_before = settings.META_SYNC_TEMPLATES_DRAIN_BUDGET
        ttl_before = TTL_WHATSAPP_TEMPLATES

        with patch("marketplace.core.pacing.ttl.mark_synced") as mark_synced, patch(
            "marketplace.core.pacing.ttl.is_recently_synced"
        ) as is_recently_synced:
            first_uc, captured, _ = self._sync(meta_templates)
            second_uc, _, _ = self._sync(meta_templates, app=other_app)

        first_uc.template_service.list_template_messages.assert_not_called()
        second_uc.template_service.list_template_messages.assert_not_called()
        mark_synced.assert_not_called()
        is_recently_synced.assert_not_called()
        self.assertEqual(settings.META_SYNC_TEMPLATES_DRAIN_BUDGET, budget_before)
        self.assertEqual(TTL_WHATSAPP_TEMPLATES, ttl_before)

        for app in (self.app, other_app):
            translation = self._translation("cota_aviso", app=app)
            self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_NAMED)
            self.assertEqual(
                [entry["param_name"] for entry in translation.body_named_params],
                ["nome", "cota"],
            )
            self.assertEqual(translation.variable_count, 2)
        self._assert_no_example_values(captured, NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA)

    def test_named_and_positional_coexist_without_contamination(self):
        named = _named_meta_template()
        positional = _positional_meta_template()
        self._sync([named, positional])

        named_translation = self._translation("cota_aviso")
        positional_translation = self._translation("pedido_enviado")

        self.assertEqual(named_translation.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            named_translation.body_named_params,
            [
                {"param_name": "nome", "example": NAMED_EXAMPLE_NOME},
                {"param_name": "cota", "example": NAMED_EXAMPLE_COTA},
            ],
        )
        self.assertEqual(named_translation.variable_count, 2)
        self.assertEqual(named_translation.body_example, [])
        self.assertIsNone(named_translation.parameter_anomaly)

        self.assertEqual(
            positional_translation.parameter_format, PARAMETER_FORMAT_POSITIONAL
        )
        self.assertEqual(positional_translation.body_named_params, [])
        self.assertEqual(positional_translation.variable_count, 0)
        self.assertEqual(
            positional_translation.body_example,
            [NAMED_EXAMPLE_NOME, POSITIONAL_EXAMPLE_ORDER],
        )
        self.assertIsNone(positional_translation.parameter_anomaly)

        named_names = {
            entry["param_name"] for entry in named_translation.body_named_params
        }
        self.assertFalse(named_names & set(positional_translation.body_example or []))
        self.assertNotIn(
            PARAMETER_FORMAT_NAMED, [positional_translation.parameter_format]
        )
        self.assertNotIn(
            PARAMETER_FORMAT_POSITIONAL, [named_translation.parameter_format]
        )

    def test_positional_sync_issues_one_list_call_for_many_templates(self):
        templates = [
            _positional_meta_template(
                template_id=str(2000 + index), name=f"pedido_{index}"
            )
            for index in range(3)
        ]
        uc = self._use_case()
        uc.template_service.list_template_messages.return_value = {"data": templates}

        with self.assertLogs(
            "marketplace.wpp_templates.usecases.template_sync", level="INFO"
        ):
            result = uc.sync_templates()

        self.assertTrue(result)
        uc.template_service.list_template_messages.assert_called_once()
        uc.template_service.create_template_message.assert_not_called()
        uc.template_service.update_template_message.assert_not_called()
        uc.template_service.get_template_namespace.assert_not_called()
        uc.template_service.get_template_analytics.assert_not_called()
        uc.template_service.delete_template_message.assert_not_called()
        for name in ("pedido_0", "pedido_1", "pedido_2"):
            translation = self._translation(name)
            self.assertEqual(translation.parameter_format, PARAMETER_FORMAT_POSITIONAL)
            self.assertEqual(translation.body_named_params, [])
            self.assertEqual(translation.variable_count, 0)

    def test_sc006_named_mirror_entries_carry_only_param_name_and_example(self):
        uc, _, _ = self._sync([_named_meta_template(), _positional_meta_template()])
        translation = self._translation("cota_aviso")
        self.assertTrue(translation.body_named_params)
        for entry in translation.body_named_params:
            self.assertEqual(set(entry), {"param_name", "example"})
        forwarded = uc.flows_client.update_facebook_templates.call_args.args[1]
        self._assert_no_positional_keys(forwarded)

    def _assert_no_positional_keys(self, node):
        forbidden = {"index", "position", "slot", "order"}
        if isinstance(node, dict):
            self.assertEqual(forbidden & set(node), set())
            for value in node.values():
                self._assert_no_positional_keys(value)
        elif isinstance(node, list):
            for item in node:
                self._assert_no_positional_keys(item)
