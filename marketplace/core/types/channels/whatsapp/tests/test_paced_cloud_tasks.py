from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import SimpleTestCase

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp.tasks import (
    sync_whatsapp_cloud_phone_numbers,
    sync_whatsapp_cloud_wabas,
    task_sync_whatsapp_cloud_phone_number_item,
    task_sync_whatsapp_cloud_waba_item,
)


def _cloud_app(uuid, waba_id, ignores=False):
    app = MagicMock()
    app.uuid = uuid
    app.config = {"wa_waba_id": waba_id} if waba_id else {}
    if ignores:
        app.config["ignores_meta_sync"] = "err"
    return app


class SyncWhatsappCloudWabasDispatcherTestCase(SimpleTestCase):
    @patch(
        "marketplace.core.types.channels.whatsapp.tasks.enqueue_item", return_value=True
    )
    @patch(
        "marketplace.core.types.channels.whatsapp.tasks.is_recently_synced",
        return_value=False,
    )
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_enqueues_one_item_per_waba(self, mock_app, mock_ttl, mock_enqueue):
        qs = MagicMock()
        qs.__iter__.return_value = iter(
            [
                _cloud_app("a1", "waba-shared"),
                _cloud_app("a2", "waba-shared"),
                _cloud_app("b1", "waba-other"),
                _cloud_app("ignored", "waba-ignored", ignores=True),
                _cloud_app("empty", None),
            ]
        )
        mock_app.objects.filter.return_value = qs

        sync_whatsapp_cloud_wabas()

        enqueued_ids = [call.args[1] for call in mock_enqueue.call_args_list]
        self.assertEqual(sorted(enqueued_ids), ["waba-other", "waba-shared"])

    @patch("marketplace.core.types.channels.whatsapp.tasks.enqueue_item")
    @patch("marketplace.core.types.channels.whatsapp.tasks.is_recently_synced")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_skips_waba_when_ttl_is_fresh(self, mock_app, mock_ttl, mock_enqueue):
        qs = MagicMock()
        qs.__iter__.return_value = iter(
            [
                _cloud_app("a1", "waba-shared"),
                _cloud_app("b1", "waba-other"),
            ]
        )
        mock_app.objects.filter.return_value = qs
        mock_ttl.side_effect = lambda key: "waba-shared" in key

        sync_whatsapp_cloud_wabas()

        enqueued_ids = [call.args[1] for call in mock_enqueue.call_args_list]
        self.assertEqual(enqueued_ids, ["waba-other"])


class SyncWhatsappCloudWabaItemTestCase(SimpleTestCase):
    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    def test_runs_sync_waba_for_waba_id(self, mock_use_case_cls):
        mock_use_case_cls.return_value.sync_waba.return_value = {"status": "synced"}

        task_sync_whatsapp_cloud_waba_item("waba-123")

        mock_use_case_cls.assert_called_once_with()
        mock_use_case_cls.return_value.sync_waba.assert_called_once_with("waba-123")

    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_uuid_shim_resolves_app_to_waba_id(self, mock_app, mock_use_case_cls):
        app_uuid = str(uuid4())
        app = MagicMock()
        app.config = {"wa_waba_id": "waba-from-app"}
        mock_app.objects.get.return_value = app
        mock_use_case_cls.return_value.sync_waba.return_value = {"status": "synced"}

        task_sync_whatsapp_cloud_waba_item(app_uuid)

        mock_app.objects.get.assert_called_once_with(uuid=app_uuid, code="wpp-cloud")
        mock_use_case_cls.return_value.sync_waba.assert_called_once_with(
            "waba-from-app"
        )

    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_uuid_shim_skips_when_app_missing(self, mock_app, mock_use_case_cls):
        mock_app.DoesNotExist = App.DoesNotExist
        mock_app.objects.get.side_effect = App.DoesNotExist()

        task_sync_whatsapp_cloud_waba_item(str(uuid4()))
        mock_use_case_cls.assert_not_called()

    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_uuid_shim_skips_when_app_has_no_waba_id(self, mock_app, mock_use_case_cls):
        app = MagicMock()
        app.config = {}
        mock_app.objects.get.return_value = app

        task_sync_whatsapp_cloud_waba_item(str(uuid4()))
        mock_use_case_cls.assert_not_called()

    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    def test_logs_error_when_sync_returns_error_status(self, mock_use_case_cls):
        mock_use_case_cls.return_value.sync_waba.return_value = {
            "status": "error",
            "error": "no_access_token",
        }

        task_sync_whatsapp_cloud_waba_item("waba-123")
        mock_use_case_cls.return_value.sync_waba.assert_called_once_with("waba-123")

    @patch("marketplace.core.types.channels.whatsapp.tasks.WABASyncUseCase")
    def test_logs_error_when_sync_raises(self, mock_use_case_cls):
        mock_use_case_cls.return_value.sync_waba.side_effect = Exception("graph down")

        task_sync_whatsapp_cloud_waba_item("waba-123")
        mock_use_case_cls.return_value.sync_waba.assert_called_once_with("waba-123")


class SyncWhatsappCloudPhoneNumbersDispatcherTestCase(SimpleTestCase):
    @patch(
        "marketplace.core.types.channels.whatsapp.tasks.enqueue_item", return_value=True
    )
    @patch(
        "marketplace.core.types.channels.whatsapp.tasks.is_recently_synced",
        return_value=False,
    )
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_enqueues_configured_cloud_apps(self, mock_app, mock_ttl, mock_enqueue):
        app = MagicMock()
        app.uuid = "app-1"
        qs = MagicMock()
        qs.__iter__.return_value = iter([app])
        qs.count.return_value = 1
        mock_app.objects.filter.return_value = qs

        sync_whatsapp_cloud_phone_numbers()
        mock_enqueue.assert_called_once()
        self.assertEqual(mock_enqueue.call_args.args[1], "app-1")

    @patch("marketplace.core.types.channels.whatsapp.tasks.enqueue_item")
    @patch("marketplace.core.types.channels.whatsapp.tasks.is_recently_synced")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_skips_app_when_ttl_is_fresh(self, mock_app, mock_ttl, mock_enqueue):
        due_app = MagicMock()
        due_app.uuid = "app-due"
        skipped_app = MagicMock()
        skipped_app.uuid = "app-skipped"
        qs = MagicMock()
        qs.__iter__.return_value = iter([skipped_app, due_app])
        qs.count.return_value = 2
        mock_app.objects.filter.return_value = qs
        mock_ttl.side_effect = lambda key: "app-skipped" in key

        sync_whatsapp_cloud_phone_numbers()

        mock_enqueue.assert_called_once()
        self.assertEqual(mock_enqueue.call_args.args[1], "app-due")


class SyncWhatsappCloudPhoneNumberItemTestCase(SimpleTestCase):
    @patch("marketplace.core.types.channels.whatsapp.tasks.PhoneNumberSyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_runs_use_case_for_existing_app(self, mock_app, mock_use_case_cls):
        app = MagicMock()
        mock_app.objects.get.return_value = app
        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.return_value = {
            "status": "synced"
        }

        task_sync_whatsapp_cloud_phone_number_item("app-1")

        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.assert_called_once()

    @patch("marketplace.core.types.channels.whatsapp.tasks.PhoneNumberSyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_logs_error_when_sync_returns_error_status(
        self, mock_app, mock_use_case_cls
    ):
        app = MagicMock()
        mock_app.objects.get.return_value = app
        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.return_value = {
            "status": "error",
            "error": "missing token",
        }

        task_sync_whatsapp_cloud_phone_number_item("app-1")
        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.assert_called_once()

    @patch("marketplace.core.types.channels.whatsapp.tasks.PhoneNumberSyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_skips_when_app_missing(self, mock_app, mock_use_case_cls):
        mock_app.DoesNotExist = App.DoesNotExist
        mock_app.objects.get.side_effect = App.DoesNotExist()

        task_sync_whatsapp_cloud_phone_number_item("app-missing")
        mock_use_case_cls.assert_not_called()

    @patch("marketplace.core.types.channels.whatsapp.tasks.PhoneNumberSyncUseCase")
    @patch("marketplace.core.types.channels.whatsapp.tasks.App")
    def test_logs_error_when_sync_raises(self, mock_app, mock_use_case_cls):
        mock_app.DoesNotExist = App.DoesNotExist
        mock_app.objects.get.return_value = MagicMock()
        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.side_effect = (
            Exception("graph down")
        )

        task_sync_whatsapp_cloud_phone_number_item("app-1")
        mock_use_case_cls.return_value.sync_whatsapp_cloud_phone_number.assert_called_once()
