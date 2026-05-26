from unittest import TestCase
from unittest.mock import MagicMock

from marketplace.services.commerce.service import CommerceService


class CommerceServiceTestCase(TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.service = CommerceService(client=self.client)

    def test_send_template_library_status_update_delegates_to_client(self):
        self.client.send_template_library_status_update.return_value = {"ok": True}
        data = {"foo": "bar"}

        result = self.service.send_template_library_status_update(data)

        self.client.send_template_library_status_update.assert_called_once_with(data)
        self.assertEqual(result, {"ok": True})

    def test_send_gallery_template_version_delegates_to_client(self):
        self.client.send_gallery_template_version.return_value = {"ok": True}

        result = self.service.send_gallery_template_version("gallery-uuid", "APPROVED")

        self.client.send_gallery_template_version.assert_called_once_with(
            "gallery-uuid", "APPROVED"
        )
        self.assertEqual(result, {"ok": True})

    def test_send_template_category_notification_delegates_to_client(self):
        self.client.send_template_category_notification.return_value = {"ok": True}
        payload = {
            "project_uuid": "proj-uuid-123",
            "app_uuid": "app-uuid-456",
            "template_name": "order_confirmation",
            "template_category": "UTILITY",
            "template_correct_category": "MARKETING",
        }

        result = self.service.send_template_category_notification(payload)

        self.client.send_template_category_notification.assert_called_once_with(payload)
        self.assertEqual(result, {"ok": True})
