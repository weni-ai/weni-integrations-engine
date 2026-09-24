from unittest.mock import MagicMock

from django.conf import settings
from django.test import SimpleTestCase

from marketplace.clients.facebook.client import (
    BusinessMetaRequests,
    BusinessVerificationRequests,
    CallingRequests,
    CatalogsRequests,
    CloudProfileRequests,
    FacebookClient,
    PhoneNumbersRequests,
    PhotoAPIRequests,
    TemplatesRequests,
)


class TemplateApiVersionTestCase(SimpleTestCase):
    def setUp(self):
        self.client = FacebookClient("test-token")
        response = MagicMock()
        response.json.return_value = {}
        self.client.make_request = MagicMock(return_value=response)

    def _requested_url(self):
        return self.client.make_request.call_args[0][0]

    def test_create_template_message_uses_template_api_url(self):
        self.client.create_template_message("waba-id", "hello", "UTILITY", [], "pt_BR")
        self.assertTrue(
            self._requested_url().startswith(settings.WHATSAPP_TEMPLATE_API_URL)
        )

    def test_list_template_messages_uses_template_api_url(self):
        self.client.list_template_messages("waba-id")
        self.assertTrue(
            self._requested_url().startswith(settings.WHATSAPP_TEMPLATE_API_URL)
        )

    def test_catalog_method_uses_whatsapp_api_url(self):
        self.client.create_catalog("biz-id", "catalog")
        self.assertTrue(self._requested_url().startswith(settings.WHATSAPP_API_URL))

    def test_templates_requests_does_not_override_base_url(self):
        self.assertNotIn("BASE_URL", TemplatesRequests.__dict__)

    def test_sibling_classes_keep_whatsapp_api_url(self):
        for cls in (
            CatalogsRequests,
            PhoneNumbersRequests,
            CloudProfileRequests,
            PhotoAPIRequests,
            CallingRequests,
            BusinessMetaRequests,
            BusinessVerificationRequests,
            FacebookClient,
        ):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(cls.BASE_URL, settings.WHATSAPP_API_URL)
