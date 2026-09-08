from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from marketplace.core.pacing.tasks import task_drain_paced_queue


class DrainPacedQueueTestCase(SimpleTestCase):
    @patch("marketplace.core.pacing.tasks.current_app")
    @patch("marketplace.core.pacing.tasks.RedisQueue")
    def test_drain_respects_budget_and_dispatches_items(self, mock_queue_cls, mock_app):
        queue = MagicMock()
        queue.get_batch.return_value = ["a", "b"]
        mock_queue_cls.return_value = queue

        with override_settings(META_SYNC_CELERY_QUEUE="meta-sync"):
            task_drain_paced_queue("paced:q", "item_task", 2)

        queue.get_batch.assert_called_once_with(2)
        self.assertEqual(mock_app.send_task.call_count, 2)
        mock_app.send_task.assert_any_call(
            "item_task", args=["a"], queue="meta-sync", ignore_result=True
        )
        mock_app.send_task.assert_any_call(
            "item_task", args=["b"], queue="meta-sync", ignore_result=True
        )

    @patch("marketplace.core.pacing.tasks.current_app")
    @patch("marketplace.core.pacing.tasks.RedisQueue")
    def test_drain_empty_queue_is_noop(self, mock_queue_cls, mock_app):
        queue = MagicMock()
        queue.get_batch.return_value = []
        mock_queue_cls.return_value = queue

        task_drain_paced_queue("paced:q", "item_task", 10)

        mock_app.send_task.assert_not_called()

    @patch("marketplace.core.pacing.tasks.current_app")
    @patch("marketplace.core.pacing.tasks.RedisQueue")
    def test_drain_zero_budget_does_not_pop(self, mock_queue_cls, mock_app):
        task_drain_paced_queue("paced:q", "item_task", 0)

        mock_queue_cls.assert_not_called()
        mock_app.send_task.assert_not_called()
