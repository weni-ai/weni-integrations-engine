from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketplace.applications.models import App
from marketplace.wpp_templates.tasks import task_sync_templates_from_meta


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
