from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.core.types.channels.whatsapp_cloud.services.flows import (
    FlowsService,
)
from marketplace.applications.models import App


User = get_user_model()


MOCK_CONFIG = {
    "title": "+55 84 99999-9999",
    "wa_pin": "12345678",
    "wa_number": "+55 84 99999-9999",
    "wa_waba_id": "123456789",
    "wa_currency": "USD",
    "wa_business_id": "202020202020",
    "wa_phone_number_id": "0123456789",
}


class MockResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


class MockFlowsClient:
    def detail_channel(self, flow_object_uuid):
        return {
            "uuid": "f32295af-9596-49f4-807e-235bdd5131f8",
            "name": "Test - Weni",
            "config": MOCK_CONFIG,
            "address": "123456789",
            "org": "518c2683-7be5-4649-9a5c-30c6999a6a97",
            "is_active": True,
        }

    def update_config(self, data, flow_object_uuid):
        return None

    def update_catalogs(self, flow_object_uuid, fba_catalog_id):
        return MockResponse(status.HTTP_200_OK)


class TestFlowsService(TestCase):
    def setUp(self):
        user, _bool = User.objects.get_or_create(email="user-fbaservice@marketplace.ai")

        self.mock_client = MockFlowsClient()
        self.service = FlowsService(client=self.mock_client)

        self.app = App.objects.create(
            code="wpp-cloud",
            config=MOCK_CONFIG,
            created_by=user,
            project_uuid="518c2683-7be5-4649-9a5c-30c6999a6a97",
            platform=App.PLATFORM_WENI_FLOWS,
        )

    def test_update_treshold(self):
        response = self.service.update_treshold(self.app, 3.5)
        self.assertEqual(response, True)

    def test_update_active_catalog(self):
        fake_facebook_catalog_id = "123456789"
        response = self.service.update_active_catalog(
            self.app, fake_facebook_catalog_id
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
