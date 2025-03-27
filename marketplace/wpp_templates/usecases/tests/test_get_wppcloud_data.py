from uuid import uuid4
from unittest import TestCase
from unittest.mock import patch, MagicMock, call

from marketplace.wpp_templates.usecases import TemplatesUseCase


class TestTemplatesUseCase(TestCase):
    @patch("marketplace.applications.models.App.objects.filter")
    @patch("marketplace.wpp_templates.models.TemplateMessage.objects.filter")
    def test_get_whatsapp_cloud_data_from_integrations(
        self, mock_template_filter, mock_app_filter
    ):
        project_uuid = uuid4()
        template_id = "test_template_id"

        app1 = MagicMock()
        app1.uuid = uuid4()
        app2 = MagicMock()
        app2.uuid = uuid4()
        mock_apps = [app1, app2]

        template1_app1 = MagicMock()
        template1_app1.uuid = uuid4()
        template2_app1 = MagicMock()
        template2_app1.uuid = uuid4()

        template1_app2 = MagicMock()
        template1_app2.uuid = uuid4()

        mock_app_filter.return_value = mock_apps

        mock_template_filter.side_effect = [
            [template1_app1, template2_app1],
            [template1_app2],
        ]

        result = TemplatesUseCase.get_whatsapp_cloud_data_from_integrations(
            project_uuid=project_uuid, template_id=template_id
        )

        mock_app_filter.assert_called_once_with(
            project_uuid=project_uuid, code="wpp-cloud", configured=True
        )

        expected_template_calls = [
            call(translations__message_template_id=template_id, app=app1),
            call(translations__message_template_id=template_id, app=app2),
        ]

        self.assertEqual(mock_template_filter.call_args_list, expected_template_calls)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].app_uuid, app1.uuid)
        self.assertEqual(len(result[0].templates_uuid), 2)
        self.assertIn(template1_app1.uuid, result[0].templates_uuid)
        self.assertIn(template2_app1.uuid, result[0].templates_uuid)
        self.assertEqual(result[1].app_uuid, app2.uuid)
        self.assertEqual(len(result[1].templates_uuid), 1)
        self.assertIn(template1_app2.uuid, result[1].templates_uuid)

        for dto in result:
            self.assertIsInstance(dto, TemplatesUseCase.WhatsappCloudDTO)
