from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.applications.models import AppTypeAsset
from marketplace.applications import types
from marketplace.applications.views import AppTypeViewSet
from marketplace.core.tests.base import APIBaseTestCase


User = get_user_model()


class AppTypeViewTestCase(APIBaseTestCase):
    def setUp(self):
        super().setUp()

        self.app_type = AppTypeAsset.objects.create(
            app_code="wwc",
            asset_type=AppTypeAsset.ASSET_TYPE_ICON,
            attachment="file_to_upload.txt",
            description="Fake",
            created_by=self.user,
        )


class ListAppTypeViewTestCase(AppTypeViewTestCase):
    url = reverse("apptypes-list")
    view_class = AppTypeViewSet

    @property
    def view(self):
        return self.view_class.as_view({"get": "list"})

    def test_request_status_ok(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_app_types_count(self):
        response = self.request.get(self.url)
        self.assertEqual(len(response.json), len(types.get_types()))

    def test_filter_app_type_by_fake_category(self):
        response = self.request.get(self.url + "?category=fake")
        self.assertEqual(response.json, [])

    def test_filter_app_type_by_right_category(self):
        response = self.request.get(self.url + "?category=channel")
        self.assertTrue(len(response.json) > 0)


class RetrieveAppTypeViewTestCase(AppTypeViewTestCase):
    url = reverse("apptypes-detail", kwargs={"pk": "wwc"})
    view_class = AppTypeViewSet

    @property
    def view(self):
        return self.view_class.as_view({"get": "retrieve"})

    def test_request_status_ok(self):
        response = self.request.get(self.url, pk="wwc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_with_invalid_code(self):
        response = self.request.get(self.url, pk="invalid")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIsNone(response.json)

    def test_retrieve_response_data(self):
        apptype = types.get_type("wwc")
        response = self.request.get(self.url, pk="wwc")
        data = response.json

        self.assertEqual(apptype.code, data["code"])
        self.assertEqual(apptype.name, data["name"])
        self.assertEqual(apptype.description, data["description"])
        self.assertEqual(apptype.summary, data["summary"])
        self.assertEqual(apptype.get_category_display(), data["category"])
        self.assertEqual(apptype.get_icon_url(), data["icon"])
        self.assertEqual(apptype.bg_color, data["bg_color"])
