import uuid

from django.urls import reverse
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from ..views import WeniWebChatViewSet
from marketplace.applications.models import App


class CreateWeniWebChatAppTestCase(APIBaseTestCase):
    url = reverse("wwc-app-list")
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()

        self.body = {
            "project_uuid": str(uuid.uuid4()),
            "platform": App.PLATFORM_WENI_FLOWS,
        }

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

    def test_create_app_without_platform(self):
        self.body.pop("platform")
        response = self.request.post(self.url, self.body)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("platform", response.json)


class RetrieveWeniWebChatAppTestCase(APIBaseTestCase):
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            app_code="wwc", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
        )

        self.url = reverse("wwc-app-detail", kwargs={"pk": self.app.pk})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, pk=self.app.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, pk=self.app.pk)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertIsNone(response.json["config"])


class ConfigureWeniWebChatAppTestCase(APIBaseTestCase):
    view_class = WeniWebChatViewSet

    def setUp(self):
        super().setUp()

        self.body = {
            "config": {
                "name": "FakeWeniWebChat",
                "dasd": 123,
                "title": "dsa",
                "avatarImage": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeA"
                "AAAA3NCSVQICAjb4U/gAAAADElEQVQImWNgYGAAAAAEAAGjChXjAAAAAElFTkSuQmCC",
                "customCss": "#teste",
                "keepHistory": True,
            }
        }

        self.app = App.objects.create(
            app_code="wwc", created_by=self.user, project_uuid=str(uuid.uuid4()), platform=App.PLATFORM_WENI_FLOWS
        )

        self.url = reverse("wwc-app-configure", kwargs={"pk": self.app.pk})

    @property
    def view(self):
        return self.view_class.as_view(dict(patch="configure"))

    def test_request_ok(self):
        response = self.request.patch(self.url, self.body, pk=self.app.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
