from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase, override_settings

from marketplace.wpp_templates.usecases.template_sync_scheduler import (
    _CLAIM_FOLLOW_UP_SCRIPT,
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
            "template_sync_scheduled:app-uuid-123", "1", nx=True, ex=60
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
        self.redis_conn.set.assert_has_calls(
            [
                call(
                    "template_sync_scheduled:app-uuid-123",
                    "1",
                    nx=True,
                    ex=60,
                ),
                call("template_sync_rerun:app-uuid-123", "1", ex=60),
            ]
        )
        mock_logger.info.assert_called_once_with(
            "Template sync already scheduled for app app-uuid-123, skipping."
        )

    @patch(
        "marketplace.wpp_templates.usecases.template_sync_scheduler.celery_app.send_task"
    )
    def test_finish_releases_reservation_when_no_webhook_arrived_during_sync(
        self, mock_send_task
    ):
        self.redis_conn.eval.return_value = 0

        self.scheduler.finish("app-uuid-123")

        self._assert_follow_up_claim("app-uuid-123")
        mock_send_task.assert_not_called()
        self.redis_conn.set.assert_not_called()

    @patch(
        "marketplace.wpp_templates.usecases.template_sync_scheduler.celery_app.send_task"
    )
    def test_finish_schedules_follow_up_when_webhook_arrived_during_sync(
        self, mock_send_task
    ):
        self.redis_conn.eval.return_value = 1

        self.scheduler.finish("app-uuid-123")

        self._assert_follow_up_claim("app-uuid-123")
        self.redis_conn.set.assert_not_called()
        mock_send_task.assert_called_once_with(
            name="task_sync_templates_from_meta",
            kwargs={"app_uuid": "app-uuid-123"},
            countdown=30,
        )

    def _assert_follow_up_claim(self, app_uuid: str) -> None:
        self.redis_conn.eval.assert_called_once_with(
            _CLAIM_FOLLOW_UP_SCRIPT,
            2,
            f"template_sync_scheduled:{app_uuid}",
            f"template_sync_rerun:{app_uuid}",
            60,
        )
