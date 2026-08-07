from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from marketplace.wpp_templates.usecases.template_sync_scheduler import (
    TemplateSyncScheduler,
)


@override_settings(TEMPLATE_SYNC_DEBOUNCE_SECONDS=30)
class TestTemplateSyncScheduler(SimpleTestCase):
    def setUp(self):
        self.redis_conn = MagicMock()
        self.scheduler = TemplateSyncScheduler(
            redis_conn=self.redis_conn, debounce_seconds=30
        )

    @patch(
        "marketplace.wpp_templates.usecases.template_sync_scheduler.celery_app.send_task"
    )
    def test_schedule_dispatches_task_when_nx_succeeds(self, mock_send_task):
        self.redis_conn.set.return_value = True

        result = self.scheduler.schedule("app-uuid-123")

        self.assertTrue(result)
        self.redis_conn.set.assert_called_once_with(
            "template_sync_scheduled:app-uuid-123", "1", nx=True, ex=30
        )
        mock_send_task.assert_called_once_with(
            name="task_sync_templates_from_meta",
            kwargs={"app_uuid": "app-uuid-123"},
            countdown=30,
        )

    @patch(
        "marketplace.wpp_templates.usecases.template_sync_scheduler.celery_app.send_task"
    )
    @patch("marketplace.wpp_templates.usecases.template_sync_scheduler.logger")
    def test_schedule_skips_when_already_scheduled(self, mock_logger, mock_send_task):
        self.redis_conn.set.return_value = False

        result = self.scheduler.schedule("app-uuid-123")

        self.assertFalse(result)
        mock_send_task.assert_not_called()
        mock_logger.info.assert_called_once_with(
            "Template sync already scheduled for app app-uuid-123, skipping."
        )
