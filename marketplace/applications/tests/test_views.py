import uuid

from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.applications.models import AppTypeAsset, App
from marketplace.interactions.models import Rating
from marketplace.core import types
from marketplace.applications.views import AppTypeViewSet, MyAppViewSet
from marketplace.core.tests.base import APIBaseTestCase


User = get_user_model()


@override_settings(USE_S3=False, USE_OIDC=False)
class AppTypeViewTestCase(APIBaseTestCase):
    def setUp(self):
        super().setUp()

        self.app_type_asset = AppTypeAsset.objects.create(
            code="wwc",
            asset_type=AppTypeAsset.ASSET_TYPE_ICON,
            attachment="file_to_upload.txt",
            description="Fake",
            created_by=self.user,
        )


class ListAppTypeViewTestCase(AppTypeViewTestCase):
    url = reverse("apptype-list")
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
    url = reverse("apptype-detail", kwargs={"pk": "wwc"})
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

    def test_retrieve_apptype_rating_without_rating_object(self):
        response = self.request.get(self.url, pk="wwc")
        rating = response.json.get("rating")

        self.assertIsNone(rating["average"])
        self.assertIsNone(rating["mine"])

    def test_retrieve_apptype_rating_with_rating_object(self):
        Rating.objects.create(created_by=self.user, rate=5, code="wwc")

        response = self.request.get(self.url, pk="wwc")
        rating = response.json.get("rating")

        self.assertEqual(rating["mine"], 5)
        self.assertEqual(rating["average"], 5.0)

    def test_retrieve_apptype_rating_created_from_other_user(self):
        Rating.objects.create(created_by=self.super_user, rate=5, code="wwc")

        response = self.request.get(self.url, pk="wwc")
        rating = response.json.get("rating")

        self.assertIsNone(rating["mine"])
        self.assertEqual(rating["average"], 5.0)

    def test_retrieve_apptype_asset_link_url(self):
        link_asset = AppTypeAsset.objects.create(
            code="wwc",
            asset_type=AppTypeAsset.ASSET_TYPE_LINK,
            url="https://dash.weni.ai",
            description="Weni dash URL",
            created_by=self.user,
        )

        response = self.request.get(self.url, pk="wwc")
        apptype_assets = response.json.get("assets")

        media = list(filter(lambda asset: "media" in asset["url"], apptype_assets))[0]
        link = list(filter(lambda asset: "https" in asset["url"], apptype_assets))[0]

        self.assertEqual(media["url"], self.app_type_asset.attachment.url)
        self.assertEqual(link["url"], link_asset.url)

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

    def test_integrations_count_value(self):
        for number in range(10):
            App.objects.create(
                code="wwc",
                config={},
                project_uuid=uuid.uuid4(),
                platform=App.PLATFORM_WENI_FLOWS,
                created_by=self.user,
            )

            response = self.request.get(self.url, pk="wwc")
            self.assertEqual(response.json["integrations_count"], number + 1)


class RetrieveMyAppViewTestCase(APIBaseTestCase):
    view_class = MyAppViewSet

    def setUp(self):
        super().setUp()
        self.app = App.objects.create(
            code="wwc",
            config={"test": "test"},
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )
        self.url = reverse("my-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_status_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        print(response.json)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
