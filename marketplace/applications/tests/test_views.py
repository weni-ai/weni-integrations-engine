import uuid

from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.applications.models import AppTypeAsset, AppTypeFeatured, App
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

    def test_metrics_value(self):
        response = self.request.get(self.url, pk="wwc")
        self.assertEqual(response.json["metrics"], 58602143)


class FeaturedsAppTypeViewTestCase(AppTypeViewTestCase):
    url = reverse("apptype-featureds")
    view_class = AppTypeViewSet

    @property
    def view(self):
        return self.view_class.as_view(dict(get="featureds"))

    def test_request_status_ok(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_featured_apptypes_without_featureds(self):
        response = self.request.get(self.url)
        self.assertEqual(response.json, [])

    def test_list_featured_apptypes_with_featureds(self):
        AppTypeFeatured.objects.create(code="wwc", created_by=self.user)
        response = self.request.get(self.url)
        self.assertEqual(len(response.json), 1)


class RetrieveMyAppViewTestCase(AppTypeViewTestCase):
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

    @property
    def query_parameter(self):
        return f"?project_uuid={self.app.project_uuid}"

    def test_request_status_ok(self):
        response = self.request.get(self.url + self.query_parameter, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_apps_without_project_uuid(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json[0], "project_uuid is a required parameter!")

    def test_retrieve_my_apps_data(self):
        response = self.request.get(self.url + self.query_parameter, uuid=self.app.uuid)
        self.assertEqual(response.json["name"], self.app.apptype.name)
        self.assertEqual(response.json["description"], self.app.apptype.description)
        self.assertEqual(response.json["summary"], self.app.apptype.summary)
        self.assertEqual(response.json["icon"], self.app_type_asset.attachment.url)
        self.assertEqual(response.json["config"], self.app.config)


class ListMyAppViewTestCase(AppTypeViewTestCase):
    url = reverse("my-app-list")
    view_class = MyAppViewSet

    def setUp(self):
        super().setUp()
        self.apps = []

        self.common_uuid = uuid.uuid4()
        self.apps_count = 10

        for num in range(self.apps_count):
            app_args = [self.common_uuid]
            if num % 2 == 1:
                app_args.append({})

            self.apps.append(self.create_app(*app_args))

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_LIST)

    def create_app(self, project_uuid: str, config: dict = dict(teste="teste")) -> App:
        return App.objects.create(
            code="wwc",
            config=config,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )

    def test_request_status_ok(self):
        response = self.request.get(self.url + f"?project_uuid={self.common_uuid}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apps_count_by_project(self):
        response = self.request.get(self.url + f"?project_uuid={self.common_uuid}")
        self.assertEqual(len(response.json), self.apps_count)

    def test_apps_count_with_another_project_uuid(self):
        new_uuid = uuid.uuid4()
        self.create_app(new_uuid)

        response = self.request.get(self.url + f"?project_uuid={new_uuid}")
        self.assertEqual(len(response.json), 1)

    def test_list_apps_without_project_uuid(self):
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json[0], "project_uuid is a required parameter!")

    def test_configured_equal_true_filter(self):
        response = self.request.get(self.url + f"?project_uuid={self.common_uuid}" + "&configured=true")
        for app in response.json:
            self.assertNotEqual(app["config"], {})

        self.assertEqual(len(response.json), 5)

    def test_configured_equal_false_filter(self):
        response = self.request.get(self.url + f"?project_uuid={self.common_uuid}" + "&configured=false")
        for app in response.json:
            self.assertEqual(app["config"], {})

        self.assertEqual(len(response.json), 5)

    def test_configured_wrong_data(self):
        response = self.request.get(self.url + f"?project_uuid={self.common_uuid}" + "&configured=test")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json[0], "Expected a boolean param in configured, but recived `test`")
