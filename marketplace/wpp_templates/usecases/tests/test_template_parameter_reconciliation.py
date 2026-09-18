import json
import os
import tempfile
import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.pacing.constants import TTL_WHATSAPP_TEMPLATES
from marketplace.wpp_templates.models import (
    PARAMETER_FORMAT_NAMED,
    PARAMETER_FORMAT_POSITIONAL,
    TemplateMessage,
    TemplateTranslation,
)
from marketplace.wpp_templates.usecases.template_parameter_reconciliation import (
    PROGRESS_KEY,
    ReconciliationCannotStartError,
    ReconciliationCannotWriteError,
    ReconciliationError,
    TemplateParameterReconciliationUseCase,
)
from marketplace.wpp_templates.usecases.template_sync import TemplateSyncUseCase
from marketplace.wpp_templates.usecases.tests.test_template_sync import (
    NAMED_BODY,
    NAMED_EXAMPLE_COTA,
    NAMED_EXAMPLE_NOME,
    POSITIONAL_BODY,
    POSITIONAL_EXAMPLE_ORDER,
    _named_meta_template,
    _positional_meta_template,
)

User = get_user_model()

RUN_ID = "2026-09-17T18:04:11Z"
EXAMPLE_VALUES = (NAMED_EXAMPLE_NOME, NAMED_EXAMPLE_COTA, POSITIONAL_EXAMPLE_ORDER)


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, *keys):
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                deleted += 1
        return deleted

    def ttl(self, key):
        return 60 if key in self.store else -2


class TemplateParameterReconciliationUseCaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.get_admin_user()
        self.redis = FakeRedis()
        self.sleep = MagicMock()
        self.logger = MagicMock()
        self.template_service = MagicMock()
        self.output_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.output_dir.cleanup)
        self.output_path = os.path.join(self.output_dir.name, "reconciliation.csv")
        self._run_id_patcher = patch.object(
            TemplateParameterReconciliationUseCase,
            "_new_run_id",
            return_value=RUN_ID,
        )
        self._run_id_patcher.start()
        self.addCleanup(self._run_id_patcher.stop)

    def _create_app(self, waba_id, extra_config=None, code="wpp-cloud"):
        config = {"wa_waba_id": waba_id, "wa_user_token": "test-token"}
        if extra_config:
            config.update(extra_config)
        return App.objects.create(
            config=config,
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code=code,
            created_by=self.user,
            flow_object_uuid=uuid.uuid4(),
        )

    def _create_translation(
        self,
        app,
        name,
        body,
        message_template_id,
        language="pt_BR",
        variable_count=0,
        parameter_format=None,
        body_named_params=None,
        parameter_anomaly=None,
    ):
        template = TemplateMessage.objects.create(
            name=name,
            app=app,
            category="UTILITY",
            template_type="TEXT",
            created_by=self.user,
        )
        return TemplateTranslation.objects.create(
            template=template,
            status="APPROVED",
            language=language,
            body=body,
            variable_count=variable_count,
            message_template_id=message_template_id,
            parameter_format=parameter_format,
            body_named_params=body_named_params or [],
            parameter_anomaly=parameter_anomaly,
        )

    def _factory(self, app):
        use_case = TemplateSyncUseCase(app)
        use_case.template_service = self.template_service
        use_case.flows_client = MagicMock()
        return use_case

    def _use_case(self):
        return TemplateParameterReconciliationUseCase(
            redis_conn=self.redis,
            sync_use_case_factory=self._factory,
            sleep=self.sleep,
            logger=self.logger,
        )

    def _execute(self, **kwargs):
        options = {
            "output": self.output_path,
            "budget": 30,
            "restart": True,
        }
        options.update(kwargs)
        return self._use_case().execute(**options)

    def _csv_text(self, path=None):
        with open(path or self.output_path, encoding="utf-8") as handle:
            return handle.read()

    def _csv_bytes(self, path=None):
        with open(path or self.output_path, "rb") as handle:
            return handle.read()

    def _logged_text(self):
        chunks = []
        for method in (self.logger.info, self.logger.warning, self.logger.error):
            for call in method.call_args_list:
                if call.args:
                    chunks.append(str(call.args[0]))
        return "\n".join(chunks)

    def _assert_no_example_values(self, text):
        for value in EXAMPLE_VALUES:
            self.assertNotIn(value, text)

    def _progress(self):
        raw = self.redis.get(PROGRESS_KEY)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    def _row_by_name(self, result, name):
        matches = [row for row in result.rows if row["template_name"] == name]
        self.assertEqual(len(matches), 1, msg=result.rows)
        return matches[0]

    def test_independent_test_broken_named_and_positional_fleet(self):
        app = self._create_app("waba-fleet")
        named = self._create_translation(
            app, "cota_aviso", NAMED_BODY, "1001", variable_count=0
        )
        positional = self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        named_meta = _named_meta_template()
        positional_meta = _positional_meta_template()
        self.template_service.list_template_messages.return_value = {
            "data": [named_meta, positional_meta]
        }

        templates_before = TemplateMessage.objects.count()
        translations_before = TemplateTranslation.objects.count()

        result = self._execute(waba_ids=["waba-fleet"])
        named.refresh_from_db()
        positional.refresh_from_db()

        self.assertEqual(named.parameter_format, PARAMETER_FORMAT_NAMED)
        self.assertEqual(
            [entry["param_name"] for entry in named.body_named_params],
            ["nome", "cota"],
        )
        self.assertEqual(named.body_named_params[0]["example"], NAMED_EXAMPLE_NOME)
        self.assertEqual(named.variable_count, 2)
        self.assertEqual(positional.parameter_format, PARAMETER_FORMAT_POSITIONAL)
        self.assertEqual(positional.variable_count, 0)

        broken = self._row_by_name(result, "cota_aviso")
        self.assertEqual(broken["category"], "corrected")
        self.assertEqual(broken["previously_broken"], "true")
        unchanged = self._row_by_name(result, "pedido_enviado")
        self.assertEqual(unchanged["category"], "unchanged")
        self.assertEqual(unchanged["previously_broken"], "false")
        self.assertEqual(TemplateMessage.objects.count(), templates_before)
        self.assertEqual(TemplateTranslation.objects.count(), translations_before)
        self._assert_no_example_values(self._csv_text())
        self._assert_no_example_values(self._logged_text())

        first_artifact = self._csv_bytes()
        named.parameter_format = None
        named.body_named_params = []
        named.variable_count = 0
        named.parameter_anomaly = None
        named.save()
        self.redis.delete(TTL_WHATSAPP_TEMPLATES.format(waba_id="waba-fleet"))
        second = self._execute(waba_ids=["waba-fleet"], restart=True)
        self.assertEqual(self._csv_bytes(), first_artifact)
        self.assertEqual(second.counters, result.counters)
        self.assertEqual(TemplateMessage.objects.count(), templates_before)
        self.assertEqual(TemplateTranslation.objects.count(), translations_before)

    def test_five_categories_are_never_conflated(self):
        app = self._create_app("waba-cats")
        self._create_translation(app, "cota_aviso", NAMED_BODY, "1001")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self._create_translation(
            app,
            "anomalous_named",
            "Olá {{nome}}",
            "1003",
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=[{"param_name": "nome", "example": "x"}],
            variable_count=1,
        )
        self._create_translation(
            app,
            "library_pending",
            "",
            "1004",
            parameter_format=None,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [
                _named_meta_template(),
                _positional_meta_template(),
                _named_meta_template(
                    template_id="1003",
                    name="anomalous_named",
                    body="Olá {{nome}}",
                    examples=[{"param_name": "outro", "example": "y"}],
                ),
            ]
        }

        result = self._execute(waba_ids=["waba-cats"])
        by_name = {row["template_name"]: row["category"] for row in result.rows}
        self.assertEqual(by_name["cota_aviso"], "corrected")
        self.assertEqual(by_name["pedido_enviado"], "unchanged")
        self.assertEqual(by_name["anomalous_named"], "anomalous")
        self.assertEqual(by_name["library_pending"], "format_not_yet_known")
        self.assertEqual(result.counters["corrected"], 1)
        self.assertEqual(result.counters["unchanged"], 1)
        self.assertEqual(result.counters["anomalous"], 1)
        self.assertEqual(result.counters["format_not_yet_known"], 1)
        self.assertEqual(result.counters["unclassifiable"], 0)

    def test_ignores_meta_sync_is_unclassifiable_and_not_classified(self):
        app = self._create_app(
            "waba-disabled", extra_config={"ignores_meta_sync": {"code": 100}}
        )
        self._create_translation(app, "cota_aviso", NAMED_BODY, "1001")
        self.template_service.list_template_messages.return_value = {
            "data": [_named_meta_template()]
        }

        result = self._execute(waba_ids=["waba-disabled"])
        row = self._row_by_name(result, "cota_aviso")
        self.assertEqual(row["category"], "unclassifiable")
        self.assertEqual(row["reason"], "sync_disabled")
        self.assertEqual(result.counters["unclassifiable"], 1)
        self.assertEqual(result.counters["corrected"], 0)
        self.assertEqual(result.counters["previously_broken"], 0)
        self.template_service.list_template_messages.assert_not_called()
        translation = TemplateTranslation.objects.get(message_template_id="1001")
        self.assertIsNone(translation.parameter_format)

    def test_meta_failure_is_unclassifiable_and_run_continues(self):
        failed = self._create_app("waba-fail")
        ok = self._create_app("waba-ok")
        self._create_translation(failed, "cota_aviso", NAMED_BODY, "1001")
        self._create_translation(
            ok,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )

        def list_messages(waba_id):
            if waba_id == "waba-fail":
                return {"error": {"code": 190, "message": "Invalid OAuth access token"}}
            return {"data": [_positional_meta_template()]}

        self.template_service.list_template_messages.side_effect = list_messages
        result = self._execute(waba_ids=["waba-fail", "waba-ok"])

        failed_row = self._row_by_name(result, "cota_aviso")
        self.assertEqual(failed_row["category"], "unclassifiable")
        self.assertEqual(failed_row["reason"], "invalid_token")
        ok_row = self._row_by_name(result, "pedido_enviado")
        self.assertEqual(ok_row["category"], "unchanged")
        self.assertEqual(result.counters["unclassifiable"], 1)
        self.assertIn("waba-fail", self._progress()["done_waba_ids"])
        self.assertIn("waba-ok", self._progress()["done_waba_ids"])

    def test_dry_run_classifies_without_writing_the_mirror(self):
        app = self._create_app("waba-dry")
        named = self._create_translation(app, "cota_aviso", NAMED_BODY, "1001")
        self.template_service.list_template_messages.return_value = {
            "data": [_named_meta_template()]
        }

        result = self._execute(waba_ids=["waba-dry"], dry_run=True)
        named.refresh_from_db()
        row = self._row_by_name(result, "cota_aviso")
        self.assertEqual(row["category"], "corrected")
        self.assertEqual(row["previously_broken"], "true")
        self.assertEqual(row["format_after"], PARAMETER_FORMAT_NAMED)
        self.assertIsNone(named.parameter_format)
        self.assertEqual(named.body_named_params, [])
        self.assertEqual(named.variable_count, 0)
        ttl_key = TTL_WHATSAPP_TEMPLATES.format(waba_id="waba-dry")
        self.assertIsNone(self.redis.get(ttl_key))

    def test_ttl_lock_skips_waba_without_rows_or_done_mark(self):
        locked = self._create_app("waba-locked")
        open_waba = self._create_app("waba-open")
        locked_translation = self._create_translation(
            locked, "cota_aviso", NAMED_BODY, "1001"
        )
        self._create_translation(
            open_waba,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.redis.set(
            TTL_WHATSAPP_TEMPLATES.format(waba_id="waba-locked"), "synced", ex=3600
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }

        result = self._execute(waba_ids=["waba-locked", "waba-open"], restart=True)
        locked_translation.refresh_from_db()
        progress = self._progress()

        self.assertEqual(result.counters["skipped_recent_sync"], 1)
        self.assertNotIn("waba-locked", progress["done_waba_ids"])
        self.assertIn("waba-open", progress["done_waba_ids"])
        self.assertFalse(any(row["waba_id"] == "waba-locked" for row in result.rows))
        self.assertIsNone(locked_translation.parameter_format)
        self.assertEqual(result.counters["corrected"], 0)
        self.assertEqual(result.counters["unclassifiable"], 0)
        self.assertEqual(result.counters["previously_broken"], 0)
        listed = [
            call.args[0]
            for call in self.template_service.list_template_messages.call_args_list
        ]
        self.assertEqual(listed, ["waba-open"])
        self.assertIn("skipped_recent_sync", self._logged_text())
        self.assertNotIn("category=skipped_recent_sync", self._csv_text())

    def test_sleep_called_with_budget_pace(self):
        app = self._create_app("waba-pace")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        self._execute(waba_ids=["waba-pace"], budget=30)
        self.sleep.assert_called_with(60 / 30)

    def test_resume_skips_done_wabas_after_truncated_progress(self):
        first = self._create_app("waba-one")
        second = self._create_app("waba-two")
        self._create_translation(
            first,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self._create_translation(second, "cota_aviso", NAMED_BODY, "1001")

        def list_messages(waba_id):
            if waba_id == "waba-one":
                return {"data": [_positional_meta_template()]}
            return {"data": [_named_meta_template()]}

        self.template_service.list_template_messages.side_effect = list_messages
        self._execute(waba_ids=["waba-one", "waba-two"], limit=1)
        progress = self._progress()
        progress["done_waba_ids"] = ["waba-one"]
        self.redis.set(PROGRESS_KEY, json.dumps(progress), ex=60 * 60 * 24)
        self.template_service.list_template_messages.reset_mock()

        result = self._execute(waba_ids=["waba-one", "waba-two"], restart=False)
        listed = [
            call.args[0]
            for call in self.template_service.list_template_messages.call_args_list
        ]
        self.assertEqual(listed, ["waba-two"])
        self.assertTrue(result.resumed)
        self.assertEqual(
            self._row_by_name(result, "cota_aviso")["category"], "corrected"
        )
        self.assertFalse(
            any(row["template_name"] == "pedido_enviado" for row in result.rows)
        )

    def test_invalid_budget_cannot_start(self):
        with self.assertRaises(ReconciliationCannotStartError):
            self._execute(budget=0)

    def test_unwritable_artifact_raises(self):
        app = self._create_app("waba-write")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        with self.assertRaises(Exception):
            self._execute(output=self.output_dir.name)

    def test_no_target_wabas_writes_header_only_and_to_dict(self):
        result = self._execute()
        self.assertEqual(result.rows, [])
        self.assertFalse(result.resumed)
        payload = result.to_dict()
        self.assertEqual(payload["run_id"], RUN_ID)
        self.assertEqual(payload["rows"], [])
        with open(self.output_path, encoding="utf-8") as handle:
            self.assertIn("run_id", handle.read())

    def test_resume_reads_progress_stored_as_bytes(self):
        app = self._create_app("waba-bytes")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        progress = {
            "run_id": RUN_ID,
            "started_at": RUN_ID,
            "done_waba_ids": [],
            "counters": {},
            "rows_written": 0,
        }
        self.redis.set(PROGRESS_KEY, json.dumps(progress).encode("utf-8"))
        result = self._execute(restart=False)
        self.assertTrue(result.resumed)
        self.assertEqual(
            self._row_by_name(result, "pedido_enviado")["category"], "unchanged"
        )

    def test_waba_ids_intersect_app_uuids(self):
        kept = self._create_app("waba-keep")
        self._create_app("waba-drop")
        self._create_translation(
            kept,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        result = self._execute(
            waba_ids=["waba-keep", "waba-drop"],
            app_uuids=[str(kept.uuid)],
        )
        listed = [
            call.args[0]
            for call in self.template_service.list_template_messages.call_args_list
        ]
        self.assertEqual(listed, ["waba-keep"])
        self.assertEqual(len(result.rows), 1)

    def test_app_uuid_filter_without_waba_ids(self):
        kept = self._create_app("waba-app-only")
        self._create_app("waba-ignored")
        self._create_translation(
            kept,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        result = self._execute(app_uuids=[str(kept.uuid)])
        listed = [
            call.args[0]
            for call in self.template_service.list_template_messages.call_args_list
        ]
        self.assertEqual(listed, ["waba-app-only"])
        self.assertEqual(len(result.rows), 1)

    def test_invalid_meta_response_is_unclassifiable(self):
        app = self._create_app("waba-invalid")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = ["not-a-dict"]
        result = self._execute()
        row = self._row_by_name(result, "pedido_enviado")
        self.assertEqual(row["category"], "unclassifiable")
        self.assertEqual(row["reason"], "invalid_meta_response")

    def test_meta_token_and_waba_gone_reasons(self):
        gone = self._create_app("waba-gone")
        token = self._create_app("waba-token")
        self._create_translation(
            gone,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self._create_translation(
            token,
            "cota_aviso",
            NAMED_BODY,
            "1001",
            variable_count=0,
        )

        def list_messages(waba_id):
            if waba_id == "waba-gone":
                return {"error": {"code": 100, "message": "Object does not exist"}}
            if waba_id == "waba-token":
                return {"error": {"code": 190, "message": "Invalid OAuth access token"}}
            return {"data": []}

        self.template_service.list_template_messages.side_effect = list_messages
        result = self._execute()
        by_waba = {row["waba_id"]: row for row in result.rows}
        self.assertEqual(by_waba["waba-gone"]["reason"], "waba_gone")
        self.assertEqual(by_waba["waba-token"]["reason"], "invalid_token")

    def test_apply_failure_marks_unclassifiable(self):
        app = self._create_app("waba-apply")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }

        def factory(target):
            use_case = self._factory(target)
            use_case.sync_templates = MagicMock(
                side_effect=RuntimeError("apply failed")
            )
            return use_case

        result = TemplateParameterReconciliationUseCase(
            redis_conn=self.redis,
            sync_use_case_factory=factory,
            sleep=self.sleep,
            logger=self.logger,
        ).execute(output=self.output_path, budget=30, restart=True)
        row = self._row_by_name(result, "pedido_enviado")
        self.assertEqual(row["category"], "unclassifiable")
        self.assertEqual(row["reason"], "apply_failed")

    def test_exception_reason_invalid_token(self):
        app = self._create_app("waba-exc")
        self._create_translation(
            app,
            "pedido_enviado",
            POSITIONAL_BODY,
            "1002",
            parameter_format=PARAMETER_FORMAT_POSITIONAL,
        )
        self.template_service.list_template_messages.side_effect = RuntimeError(
            "expired token"
        )
        result = self._execute()
        self.assertEqual(
            self._row_by_name(result, "pedido_enviado")["reason"], "invalid_token"
        )

    def test_dry_run_unmatched_template_is_format_not_yet_known(self):
        app = self._create_app("waba-unmatched")
        self._create_translation(
            app,
            "ghost",
            "",
            "9999",
            parameter_format=None,
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_positional_meta_template()]
        }
        result = self._execute(dry_run=True)
        self.assertEqual(
            self._row_by_name(result, "ghost")["category"], "format_not_yet_known"
        )

    def test_named_format_without_stored_names_is_not_previously_broken(self):
        app = self._create_app("waba-named-empty")
        self._create_translation(
            app,
            "cota_aviso",
            NAMED_BODY,
            "1001",
            variable_count=0,
            parameter_format=PARAMETER_FORMAT_NAMED,
            body_named_params=[],
        )
        self.template_service.list_template_messages.return_value = {
            "data": [_named_meta_template()]
        }
        result = self._execute()
        row = self._row_by_name(result, "cota_aviso")
        self.assertEqual(row["previously_broken"], "false")

    def test_classify_none_post_is_unclassifiable(self):
        self.assertEqual(
            self._use_case()._classify(MagicMock(), None), "unclassifiable"
        )

    def test_snapshot_translations_empty_when_no_apps(self):
        self.assertEqual(
            self._use_case()._snapshot_translations([], "waba-x", set()),
            [],
        )

    def test_ghost_waba_is_marked_done_without_rows(self):
        result = self._execute(waba_ids=["ghost-waba"])
        self.assertEqual(result.rows, [])
        self.assertIn("ghost-waba", self._progress()["done_waba_ids"])

    def test_meta_error_reason_fallbacks(self):
        use_case = self._use_case()
        self.assertEqual(use_case._meta_error_reason("plain"), "plain")
        self.assertEqual(use_case._meta_error_reason({"code": 77}), "77")
        self.assertEqual(use_case._meta_error_reason({}), "meta_error")

    def test_exception_reason_uses_class_name_when_empty(self):
        class EmptyError(Exception):
            def __str__(self):
                return ""

        self.assertEqual(self._use_case()._exception_reason(EmptyError()), "EmptyError")

    def test_progress_read_failure_cannot_start(self):
        redis = MagicMock()
        redis.get.side_effect = RuntimeError("redis down")
        use_case = TemplateParameterReconciliationUseCase(
            redis_conn=redis,
            sync_use_case_factory=self._factory,
            sleep=self.sleep,
            logger=self.logger,
        )
        with self.assertRaises(ReconciliationCannotStartError):
            use_case.execute(output=self.output_path, restart=False)

    def test_progress_delete_failure_on_restart_cannot_start(self):
        redis = MagicMock()
        redis.delete.side_effect = RuntimeError("redis down")
        use_case = TemplateParameterReconciliationUseCase(
            redis_conn=redis,
            sync_use_case_factory=self._factory,
            sleep=self.sleep,
            logger=self.logger,
        )
        with self.assertRaises(ReconciliationCannotStartError):
            use_case.execute(output=self.output_path, restart=True)

    def test_process_loop_oserror_is_cannot_write(self):
        self._create_app("waba-os")
        use_case = self._use_case()
        with patch.object(use_case, "_process_waba", side_effect=OSError("disk")):
            with self.assertRaises(ReconciliationCannotWriteError):
                use_case.execute(output=self.output_path, budget=30, restart=True)

    def test_header_only_unwritable_path_raises(self):
        with self.assertRaises(ReconciliationCannotWriteError):
            self._execute(output="/no/such/dir/out.csv")

    def test_emit_rows_writerow_oserror_is_cannot_write(self):
        writer = MagicMock()
        writer.writerow.side_effect = OSError("disk")
        progress = {"counters": {}, "rows_written": 0}
        with self.assertRaises(ReconciliationCannotWriteError):
            self._use_case()._emit_waba_rows(
                [
                    {
                        "category": "unchanged",
                        "_previously_broken": False,
                        "run_id": RUN_ID,
                    }
                ],
                progress,
                [],
                writer,
                MagicMock(),
            )

    def test_emit_rows_flush_oserror_is_cannot_write(self):
        writer = MagicMock()
        writer_file = MagicMock()
        writer_file.flush.side_effect = OSError("disk")
        progress = {"counters": {}, "rows_written": 0}
        with self.assertRaises(ReconciliationCannotWriteError):
            self._use_case()._emit_waba_rows(
                [
                    {
                        "category": "unchanged",
                        "_previously_broken": False,
                        "run_id": RUN_ID,
                    }
                ],
                progress,
                [],
                writer,
                writer_file,
            )

    def test_process_loop_cannot_write_is_reraised(self):
        self._create_app("waba-write")
        use_case = self._use_case()
        with patch.object(
            use_case,
            "_process_waba",
            side_effect=ReconciliationCannotWriteError("disk"),
        ):
            with self.assertRaises(ReconciliationCannotWriteError):
                use_case.execute(output=self.output_path, budget=30, restart=True)

    def test_progress_reconciliation_error_is_reraised(self):
        use_case = self._use_case()
        with patch.object(
            use_case,
            "_read_progress",
            side_effect=ReconciliationError("progress"),
        ):
            with self.assertRaises(ReconciliationError):
                use_case.execute(output=self.output_path, restart=False)

    def test_read_progress_returns_none_when_missing(self):
        self.assertIsNone(self._use_case()._read_progress())

    def test_new_run_id_uses_utc_timestamp(self):
        self._run_id_patcher.stop()
        try:
            run_id = TemplateParameterReconciliationUseCase._new_run_id()
        finally:
            self._run_id_patcher.start()
        self.assertRegex(run_id, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
