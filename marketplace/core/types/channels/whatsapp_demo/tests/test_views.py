import uuid

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import WhatsAppDemoViewSet
from marketplace.applications.models import App


class CreateWhatsAppDemoAppTestCase(APIBaseTestCase):
    url = reverse("whatsapp_demo-app-list")
    view_class = WhatsAppDemoViewSet

    def setUp(self):
        super().setUp()

        self.body = {"project_uuid": str(uuid.uuid4())}

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_request_ok(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_uuid", response.json)

    def test_create_app_platform(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_WENI_FLOWS)

    def test_get_app_with_respective_project_uuid(self):
        self.request.post(self.url, self.body)
        App.objects.get(project_uuid=self.body.get("project_uuid"))
