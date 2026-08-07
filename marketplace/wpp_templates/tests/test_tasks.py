from unittest.mock import MagicMock, call, patch

from django.test import SimpleTestCase

from marketplace.applications.models import App
from marketplace.wpp_templates.tasks import (
    task_sync_templates_from_meta,
    update_templates_by_webhook,
)


class TestTaskSyncTemplatesFromMeta(SimpleTestCase):
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks.App.objects.get")
    def test_happy_path_syncs_templates(self, mock_get, mock_sync_cls):
        app = MagicMock()
        mock_get.return_value = app
        sync_instance = MagicMock()
        mock_sync_cls.return_value = sync_instance

        task_sync_templates_from_meta("app-uuid-123")

        mock_get.assert_called_once_with(uuid="app-uuid-123")
        mock_sync_cls.assert_called_once_with(app)
        sync_instance.sync_templates.assert_called_once_with()

    @patch("marketplace.wpp_templates.tasks.logger")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks.App.objects.get")
    def test_app_does_not_exist_is_logged(self, mock_get, mock_sync_cls, mock_logger):
        mock_get.side_effect = App.DoesNotExist

        task_sync_templates_from_meta("missing-uuid")

        mock_sync_cls.assert_not_called()
        mock_logger.error.assert_called_once()
        self.assertIn("missing-uuid", mock_logger.error.call_args.args[0])

    @patch("marketplace.wpp_templates.tasks.logger")
    @patch("marketplace.wpp_templates.tasks.TemplateSyncUseCase")
    @patch("marketplace.wpp_templates.tasks.App.objects.get")
    def test_sync_exception_is_logged(self, mock_get, mock_sync_cls, mock_logger):
        app = MagicMock()
        mock_get.return_value = app
        sync_instance = MagicMock()
        sync_instance.sync_templates.side_effect = Exception("Meta rate limit")
        mock_sync_cls.return_value = sync_instance

        task_sync_templates_from_meta("app-uuid-123")

        mock_logger.error.assert_called_once()
        self.assertIn("Meta rate limit", mock_logger.error.call_args.args[0])
        self.assertIn("app-uuid-123", mock_logger.error.call_args.args[0])


def _status_change(template_name="order_confirmation", reason=""):
    return {
        "field": "message_template_status_update",
        "value": {
            "event": "APPROVED",
            "message_template_id": 9988776655443322,
            "message_template_name": template_name,
            "message_template_language": "en_US",
            "reason": reason,
        },
    }


class TestUpdateTemplatesByWebhook(SimpleTestCase):
    def test_task_options_enable_late_ack_and_reject_on_worker_lost(self):
        self.assertTrue(update_templates_by_webhook.acks_late)
        self.assertTrue(update_templates_by_webhook.reject_on_worker_lost)

    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_batch_with_two_entries_and_two_changes_each_reaches_processor_four_times(
        self, mock_factory
    ):
        processor = MagicMock()
        mock_factory.return_value = processor

        webhook_data = {
            "entry": [
                {
                    "id": "waba-1",
                    "changes": [
                        _status_change("tpl_a"),
                        _status_change("tpl_b"),
                    ],
                },
                {
                    "id": "waba-2",
                    "changes": [
                        _status_change("tpl_c"),
                        _status_change("tpl_d"),
                    ],
                },
            ]
        }

        update_templates_by_webhook(webhook_data=webhook_data)

        self.assertEqual(processor.process_event.call_count, 4)
        processor.process_event.assert_has_calls(
            [
                call(
                    "waba-1",
                    webhook_data["entry"][0]["changes"][0]["value"],
                    "message_template_status_update",
                    webhook_data,
                ),
                call(
                    "waba-1",
                    webhook_data["entry"][0]["changes"][1]["value"],
                    "message_template_status_update",
                    webhook_data,
                ),
                call(
                    "waba-2",
                    webhook_data["entry"][1]["changes"][0]["value"],
                    "message_template_status_update",
                    webhook_data,
                ),
                call(
                    "waba-2",
                    webhook_data["entry"][1]["changes"][1]["value"],
                    "message_template_status_update",
                    webhook_data,
                ),
            ]
        )

    @patch("marketplace.wpp_templates.tasks.logger")
    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_change_with_none_value_is_skipped_and_following_changes_still_process(
        self, mock_factory, mock_logger
    ):
        processor = MagicMock()
        mock_factory.return_value = processor
        good_change = _status_change("good")

        webhook_data = {
            "entry": [
                {
                    "id": "waba-1",
                    "changes": [
                        {
                            "field": "message_template_status_update",
                            "value": None,
                        },
                        good_change,
                    ],
                }
            ]
        }

        update_templates_by_webhook(webhook_data=webhook_data)

        processor.process_event.assert_called_once_with(
            "waba-1",
            good_change["value"],
            "message_template_status_update",
            webhook_data,
        )
        mock_logger.warning.assert_called_once()
        self.assertIn("has no value", mock_logger.warning.call_args.args[0])

    @patch("marketplace.wpp_templates.tasks.logger")
    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_processor_exception_on_first_change_does_not_stop_second(
        self, mock_factory, mock_logger
    ):
        processor = MagicMock()
        processor.process_event.side_effect = [Exception("boom"), None]
        mock_factory.return_value = processor

        first = _status_change("first")
        second = _status_change("second")
        webhook_data = {
            "entry": [
                {
                    "id": "waba-1",
                    "changes": [first, second],
                }
            ]
        }

        update_templates_by_webhook(webhook_data=webhook_data)

        self.assertEqual(processor.process_event.call_count, 2)
        mock_logger.error.assert_called_once()
        self.assertTrue(mock_logger.error.call_args.kwargs.get("exc_info"))

    @patch("marketplace.wpp_templates.tasks.logger")
    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_unmapped_field_logs_and_never_calls_processor(
        self, mock_factory, mock_logger
    ):
        processor = MagicMock()
        mock_factory.return_value = processor

        update_templates_by_webhook(
            webhook_data={
                "entry": [
                    {
                        "id": "waba-1",
                        "changes": [
                            {
                                "field": "phone_number_name_update",
                                "value": {"display_phone_number": "123"},
                            }
                        ],
                    }
                ]
            }
        )

        processor.process_event.assert_not_called()
        mock_logger.info.assert_any_call(
            "Event: phone_number_name_update, not mapped to usage"
        )

    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_absent_webhook_data_is_noop(self, mock_factory):
        processor = MagicMock()
        mock_factory.return_value = processor

        update_templates_by_webhook()

        processor.process_event.assert_not_called()

    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_none_webhook_data_is_noop(self, mock_factory):
        processor = MagicMock()
        mock_factory.return_value = processor

        update_templates_by_webhook(webhook_data=None)

        processor.process_event.assert_not_called()

    @patch("marketplace.wpp_templates.tasks.create_template_webhook_event_processor")
    def test_reason_none_is_normalized_to_empty_string_before_dispatch(
        self, mock_factory
    ):
        processor = MagicMock()
        mock_factory.return_value = processor
        change = _status_change(reason=None)

        webhook_data = {"entry": [{"id": "waba-1", "changes": [change]}]}

        update_templates_by_webhook(webhook_data=webhook_data)

        dispatched_value = processor.process_event.call_args.args[1]
        self.assertEqual(dispatched_value["reason"], "")
