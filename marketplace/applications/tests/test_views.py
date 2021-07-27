from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from marketplace.applications.models import AppTypeAsset
from marketplace.applications import types


User = get_user_model()


class AppTypeViewTestCase(TestCase):
    URL: str

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.app_type = AppTypeAsset.objects.create(
            app_code="wwc",
            asset_type=AppTypeAsset.ASSET_TYPE_ICON,
            attachment="file_to_upload.txt",
            description="Fake",
            created_by=self.user,
        )

        self.client = APIClient()


class ListAppTypeViewTestCase(AppTypeViewTestCase):
    URL = reverse("apptypes-list")

    def test_request_status_ok(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_app_types_count(self):
        response = self.client.get(self.URL)
        self.assertEqual(len(response.json()), len(types.get_types()))

    def test_filter_app_type_by_fake_category(self):
        response = self.client.get(self.URL + "?category=fake")
        self.assertEqual(response.json(), [])

    def test_filter_app_type_by_right_category(self):
        response = self.client.get(self.URL + "?category=channel")
        self.assertTrue(len(response.json()) > 0)


class RetrieveAppTypeViewTestCase(AppTypeViewTestCase):
    URL = reverse("apptypes-detail", kwargs={"pk": "wwc"})

    def test_request_status_ok(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_with_invalid_code(self):
        url = reverse("apptypes-detail", kwargs={"pk": "invalid"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(bool(response.content))

    def test_retrieve_response_data(self):
        apptype = types.get_type("wwc")
        response = self.client.get(self.URL)
        data = response.json()

        self.assertEqual(apptype.code, data["code"])
        self.assertEqual(apptype.name, data["name"])
        self.assertEqual(apptype.description, data["description"])
        self.assertEqual(apptype.summary, data["summary"])
        self.assertEqual(apptype.get_category_display(), data["category"])
        self.assertEqual(apptype.get_icon_url(), data["icon"])
        self.assertEqual(apptype.bg_color, data["bg_color"])
