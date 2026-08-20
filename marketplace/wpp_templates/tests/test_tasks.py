from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketplace.wpp_templates.tasks import (
    _apps_for_waba,
    _resolve_waba_id,
    refresh_whatsapp_templates_from_facebook,
    task_sync_whatsapp_templates_item,
)


def _app(uuid, waba_id, ignores=False):
    app = MagicMock()
    app.uuid = uuid
    app.config = {"wa_waba_id": waba_id}
    if ignores:
        app.config["ignores_meta_sync"] = "err"
    return app


class RefreshWhatsappTemplatesDispatcherTestCase(SimpleTestCase):
    @patch("marketplace.wpp_templates.tasks.enqueue_item", return_value=True)
    @patch("marketplace.wpp_templates.tasks.is_recently_synced", return_value=False)
    @patch("marketplace.wpp_templates.tasks.App")
    def test_enqueues_one_item_per_waba(self, mock_app, mock_ttl, mock_enqueue):
        mock_app.objects.filter.return_value = [
            _app("a1", "waba-shared"),
            _app("a2", "waba-shared"),
            _app("b1", "waba-other"),
            _app("ignored", "waba-ignored", ignores=True),
            _app("empty", None),
        ]

        refresh_whatsapp_templates_from_facebook()

        enqueued_ids = [call.args[1] for call in mock_enqueue.call_args_list]
        self.assertEqual(sorted(enqueued_ids), ["waba-other", "waba-shared"])

    @patch("marketplace.wpp_templates.tasks.enqueue_item", return_value=True)
    @patch("marketplace.wpp_templates.tasks.is_recently_synced")
    @patch("marketplace.wpp_templates.tasks.App")
    def test_skips_waba_when_ttl_is_fresh(self, mock_app, mock_ttl, mock_enqueue):
        mock_app.objects.filter.return_value = [
            _app("a1", "waba-shared"),
            _app("b1", "waba-other"),
        ]
        mock_ttl.side_effect = lambda key: "waba-shared" in key

        refresh_whatsapp_templates_from_facebook()

        enqueued_ids = [call.args[1] for call in mock_enqueue.call_args_list]
        self.assertEqual(enqueued_ids, ["waba-other"])

    @patch("marketplace.wpp_templates.tasks.enqueue_item")
    @patch("marketplace.wpp_templates.tasks._resolve_waba_id")
    @patch("marketplace.wpp_templates.tasks.App")
    def test_logs_error_when_enqueue_raises(self, mock_app, mock_resolve, mock_enqueue):
        mock_app.objects.filter.return_value = [_app("a1", "waba-shared")]
        mock_resolve.side_effect = Exception("redis down")

        refresh_whatsapp_templates_from_facebook()

        mock_enqueue.assert_not_called()


class SyncWhatsappTemplatesItemTestCase(SimpleTestCase):
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks._apps_for_waba")
    def test_returns_early_when_no_eligible_apps(
        self, mock_apps_for_waba, mock_use_case_cls
    ):
        mock_apps_for_waba.return_value = []
        task_sync_whatsapp_templates_item("waba-shared")
        mock_use_case_cls.assert_not_called()

    @patch("marketplace.wpp_templates.tasks.mark_synced")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks._apps_for_waba")
    def test_fetches_once_and_applies_to_all_apps(
        self, mock_apps_for_waba, mock_use_case_cls, mock_mark
    ):
        mock_apps_for_waba.return_value = [
            _app("a1", "waba-shared"),
            _app("a2", "waba-shared"),
        ]
        representative = MagicMock()
        representative.template_service.list_template_messages.return_value = {
            "data": [{"id": "1"}]
        }
        apply_use_case = MagicMock()
        mock_use_case_cls.side_effect = [representative, apply_use_case, apply_use_case]

        task_sync_whatsapp_templates_item("waba-shared")

        representative.template_service.list_template_messages.assert_called_once_with(
            "waba-shared"
        )
        self.assertEqual(apply_use_case.sync_templates.call_count, 2)
        mock_mark.assert_called_once()

    @patch("marketplace.wpp_templates.tasks.mark_synced")
    @patch("marketplace.wpp_templates.tasks.handle_error_and_update_config")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks._apps_for_waba")
    def test_does_not_mark_ttl_when_meta_returns_error(
        self, mock_apps_for_waba, mock_use_case_cls, mock_handle, mock_mark
    ):
        mock_apps_for_waba.return_value = [_app("a1", "waba-shared")]
        representative = MagicMock()
        representative.template_service.list_template_messages.return_value = {
            "error": {"code": 4}
        }
        mock_use_case_cls.return_value = representative

        task_sync_whatsapp_templates_item("waba-shared")

        mock_handle.assert_called_once()
        mock_mark.assert_not_called()

    @patch("marketplace.wpp_templates.tasks.mark_synced")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks._apps_for_waba")
    def test_continues_when_applying_templates_raises(
        self, mock_apps_for_waba, mock_use_case_cls, mock_mark
    ):
        mock_apps_for_waba.return_value = [
            _app("a1", "waba-shared"),
            _app("a2", "waba-shared"),
        ]
        representative = MagicMock()
        representative.template_service.list_template_messages.return_value = {
            "data": [{"id": "1"}]
        }
        apply_use_case = MagicMock()
        apply_use_case.sync_templates.side_effect = [Exception("apply failed"), None]
        mock_use_case_cls.side_effect = [representative, apply_use_case, apply_use_case]

        task_sync_whatsapp_templates_item("waba-shared")

        self.assertEqual(apply_use_case.sync_templates.call_count, 2)
        mock_mark.assert_called_once()

    @patch("marketplace.wpp_templates.tasks.mark_synced")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks._apps_for_waba")
    def test_logs_error_when_item_processing_raises(
        self, mock_apps_for_waba, mock_use_case_cls, mock_mark
    ):
        mock_apps_for_waba.return_value = [_app("a1", "waba-shared")]
        mock_use_case_cls.side_effect = Exception("boom")

        task_sync_whatsapp_templates_item("waba-shared")

        mock_mark.assert_not_called()


class AppsForWabaTestCase(SimpleTestCase):
    @patch("marketplace.wpp_templates.tasks.App")
    def test_filters_out_apps_that_ignore_meta_sync(self, mock_app):
        eligible = _app("a1", "waba-shared")
        ignored = _app("ignored", "waba-shared", ignores=True)
        qs = MagicMock()
        qs.__iter__.return_value = iter([eligible, ignored])
        mock_app.objects.filter.return_value.filter.return_value = qs

        apps = _apps_for_waba("waba-shared")
        self.assertEqual(apps, [eligible])


class ResolveWabaIdTestCase(SimpleTestCase):
    def test_prefers_wa_waba_id(self):
        app = MagicMock()
        app.config = {"wa_waba_id": "direct", "waba": {"id": "nested"}}
        self.assertEqual(_resolve_waba_id(app), "direct")

    def test_falls_back_to_nested_waba_id(self):
        app = MagicMock()
        app.config = {"waba": {"id": "nested"}}
        self.assertEqual(_resolve_waba_id(app), "nested")
