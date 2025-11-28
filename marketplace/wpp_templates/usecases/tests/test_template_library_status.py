from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase
import json

from marketplace.wpp_templates.usecases.template_library_status import (
    TemplateLibraryStatusUseCase,
)


class TestTemplateLibraryStatusUseCase(SimpleTestCase):
    """Unit tests for TemplateLibraryStatusUseCase using dependency injection and mocks."""

    def _make_app(self):
        app = MagicMock()
        app.uuid = "app-uuid-123"
        return app

    def _make_uc(self, redis_conn=None, commerce_service=None):
        return TemplateLibraryStatusUseCase(
            app=self._make_app(),
            redis_conn=redis_conn or MagicMock(),
            commerce_service=commerce_service or MagicMock(),
        )

    def test_update_template_status_no_redis_entry(self):
        """When there is no stored status, update should no-op."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = None
        uc = self._make_uc(redis_conn=redis_conn)
        uc._update_redis_status = MagicMock()

        uc.update_template_status("any", "APPROVED")

        uc._update_redis_status.assert_not_called()

    def test_update_template_status_rejected_keeps_state(self):
        """If current status is REJECTED/ERROR, keep it and persist unchanged."""
        statuses = {"t1": "REJECTED"}
        redis_conn = MagicMock()
        redis_conn.get.return_value = json.dumps(statuses).encode("utf-8")
        uc = self._make_uc(redis_conn=redis_conn)
        uc._update_redis_status = MagicMock()

        uc.update_template_status("t1", "APPROVED")

        uc._update_redis_status.assert_called_once()
        sent = uc._update_redis_status.call_args.args[0]
        self.assertEqual(sent["t1"], "REJECTED")

    def test_update_template_status_updates_value(self):
        """If current status is not REJECTED/ERROR, it should be updated and persisted."""
        statuses = {"t1": "APPROVED"}
        redis_conn = MagicMock()
        redis_conn.get.return_value = json.dumps(statuses).encode("utf-8")
        uc = self._make_uc(redis_conn=redis_conn)
        uc._update_redis_status = MagicMock()

        uc.update_template_status("t1", "PENDING")

        sent = uc._update_redis_status.call_args.args[0]
        self.assertEqual(sent["t1"], "PENDING")

    def test_update_template_status_missing_name(self):
        """If template name not present, do not persist."""
        statuses = {"t1": "APPROVED"}
        redis_conn = MagicMock()
        redis_conn.get.return_value = json.dumps(statuses).encode("utf-8")
        uc = self._make_uc(redis_conn=redis_conn)
        uc._update_redis_status = MagicMock()

        uc.update_template_status("t2", "PENDING")

        uc._update_redis_status.assert_not_called()

    def test_synchronize_all_stored_templates_none(self):
        """No statuses -> returns early without completing process."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = None
        uc = self._make_uc(redis_conn=redis_conn)
        uc._complete_sync_process_if_no_pending = MagicMock()

        uc.synchronize_all_stored_templates(skip_facebook_sync=True)

        uc._complete_sync_process_if_no_pending.assert_not_called()

    def test_synchronize_all_stored_templates_calls_complete(self):
        """Existing statuses -> delegates to completion method with flag."""
        statuses = {"a": "APPROVED"}
        redis_conn = MagicMock()
        redis_conn.get.return_value = json.dumps(statuses).encode("utf-8")
        uc = self._make_uc(redis_conn=redis_conn)
        uc._complete_sync_process_if_no_pending = MagicMock()

        uc.synchronize_all_stored_templates(skip_facebook_sync=True)

        uc._complete_sync_process_if_no_pending.assert_called_once()
        args, kwargs = uc._complete_sync_process_if_no_pending.call_args
        self.assertEqual(args[0], statuses)
        self.assertTrue(args[1])

    def test_complete_sync_no_pending_with_fb_sync(self):
        """No pending and not skipping -> sync from FB, notify commerce and cleanup Redis."""
        statuses = {"a": "APPROVED", "b": "APPROVED"}
        redis_conn = MagicMock()
        uc = self._make_uc(redis_conn=redis_conn)
        uc.sync_templates_from_facebook = MagicMock()
        uc.notify_commerce_module = MagicMock()

        uc._complete_sync_process_if_no_pending(statuses, skip_facebook_sync=False)

        uc.sync_templates_from_facebook.assert_called_once_with(uc.app)
        uc.notify_commerce_module.assert_called_once_with(statuses)
        redis_conn.delete.assert_called_once_with(uc.redis_key)

    def test_complete_sync_no_pending_skip_fb(self):
        """No pending and skipping -> only notify and cleanup; no FB sync."""
        statuses = {"a": "APPROVED"}
        redis_conn = MagicMock()
        uc = self._make_uc(redis_conn=redis_conn)
        uc.sync_templates_from_facebook = MagicMock()
        uc.notify_commerce_module = MagicMock()

        uc._complete_sync_process_if_no_pending(statuses, skip_facebook_sync=True)

        uc.sync_templates_from_facebook.assert_not_called()
        uc.notify_commerce_module.assert_called_once_with(statuses)
        redis_conn.delete.assert_called_once_with(uc.redis_key)

    def test_complete_sync_with_pending(self):
        """Has pending -> do not sync/notify/delete."""
        statuses = {"a": "PENDING", "b": "APPROVED"}
        redis_conn = MagicMock()
        uc = self._make_uc(redis_conn=redis_conn)
        uc.sync_templates_from_facebook = MagicMock()
        uc.notify_commerce_module = MagicMock()

        uc._complete_sync_process_if_no_pending(statuses, skip_facebook_sync=False)

        uc.sync_templates_from_facebook.assert_not_called()
        uc.notify_commerce_module.assert_not_called()
        redis_conn.delete.assert_not_called()

    def test_get_template_statuses_none(self):
        """When Redis has no value, returns empty dict."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = None
        uc = self._make_uc(redis_conn=redis_conn)

        out = uc._get_template_statuses_from_redis()
        self.assertEqual(out, {})

    def test_get_template_statuses_valid_bytes(self):
        """When Redis returns valid JSON bytes, loads and returns dict."""
        statuses = {"x": "APPROVED"}
        redis_conn = MagicMock()
        redis_conn.get.return_value = json.dumps(statuses).encode("utf-8")
        uc = self._make_uc(redis_conn=redis_conn)

        out = uc._get_template_statuses_from_redis()
        self.assertEqual(out, statuses)

    def test_get_template_statuses_invalid_json(self):
        """Invalid JSON should be handled by deleting key and returning empty dict."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = b"invalid"
        uc = self._make_uc(redis_conn=redis_conn)

        out = uc._get_template_statuses_from_redis()
        self.assertEqual(out, {})
        redis_conn.delete.assert_called_once_with(uc.redis_key)

    def test_update_redis_status_sets_with_ttl(self):
        """_update_redis_status should set serialized value with expiration."""
        redis_conn = MagicMock()
        uc = self._make_uc(redis_conn=redis_conn)
        data = {"a": "APPROVED"}

        uc._update_redis_status(data)

        redis_conn.set.assert_called_once()
        key, payload = redis_conn.set.call_args.args[:2]
        kwargs = redis_conn.set.call_args.kwargs
        self.assertEqual(key, uc.redis_key)
        self.assertEqual(json.loads(payload), data)
        self.assertEqual(kwargs.get("ex"), 60 * 60 * 24)

    def test_notify_commerce_module_calls_service(self):
        """notify_commerce_module should call commerce service and return its response."""
        commerce_service = MagicMock()
        commerce_service.send_template_library_status_update.return_value = {"ok": True}
        uc = self._make_uc(commerce_service=commerce_service)

        res = uc.notify_commerce_module({"a": "APPROVED"})

        commerce_service.send_template_library_status_update.assert_called_once()
        self.assertEqual(res, {"ok": True})

    def test_store_pending_templates_status_delegates(self):
        """store_pending_templates_status should delegate to _update_redis_status."""
        uc = self._make_uc()
        uc._update_redis_status = MagicMock()
        payload = {"t1": "PENDING"}

        uc.store_pending_templates_status(payload)

        uc._update_redis_status.assert_called_once_with(payload)

    def test_cancel_scheduled_sync_nothing(self):
        """cancel_scheduled_sync should no-op when no task id is present."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = None
        uc = self._make_uc(redis_conn=redis_conn)

        uc.cancel_scheduled_sync()

        redis_conn.delete.assert_not_called()

    def test_cancel_scheduled_sync_deletes(self):
        """cancel_scheduled_sync should delete task key when present."""
        redis_conn = MagicMock()
        redis_conn.get.return_value = "task-id"
        uc = self._make_uc(redis_conn=redis_conn)

        uc.cancel_scheduled_sync()

        redis_conn.delete.assert_called_once()

    def test_sync_templates_from_facebook_calls_use_case(self):
        """sync_templates_from_facebook should instantiate TemplateSyncUseCase and call sync."""
        uc = self._make_uc()
        with patch(
            "marketplace.wpp_templates.usecases.template_library_status.TemplateSyncUseCase"
        ) as mock_cls:
            instance = MagicMock()
            mock_cls.return_value = instance

            uc.sync_templates_from_facebook(uc.app)

            mock_cls.assert_called_once_with(uc.app)
            instance.sync_templates.assert_called_once_with()
