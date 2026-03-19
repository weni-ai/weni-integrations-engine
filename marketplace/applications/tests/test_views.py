import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import override_settings, TestCase
from django.utils import timezone
from rest_framework import status

from marketplace.applications.models import AppTypeAsset, AppTypeFeatured, App
from marketplace.applications.views import AppTypeViewSet, MyAppViewSet, PreverifiedPhoneNumber
from marketplace.clients.exceptions import CustomAPIException
from marketplace.clients.facebook.client import FacebookClient
from marketplace.interactions.models import Rating
from marketplace.core import types
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.tests.mixis.permissions import PermissionTestCaseMixin


User = get_user_model()


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
        # TODO: remove the `- 1`
        # Removing -1 (generic-apptype)
        self.assertEqual(len(response.json), len(types.APPTYPES) - 2)

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
        apptype = types.APPTYPES.get("wwc")
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
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
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

        self.project_uuid = uuid.uuid4()
        self.apps_count = 10
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid
        )

        for num in range(self.apps_count):
            app_args = [self.project_uuid]
            if num % 2 == 1:
                app_args.append({})
                app_args.append(False)
            else:
                app_args.append(dict(teste="test"))
                app_args.append(True)

            self.apps.append(self.create_app(*app_args))

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_LIST)

    def create_app(
        self,
        project_uuid: str,
        config: dict = dict(teste="teste"),
        configured: bool = True,
    ) -> App:
        return App.objects.create(
            code="wwc",
            config=config,
            configured=configured,
            project_uuid=project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )

    def test_request_status_ok(self):
        response = self.request.get(self.url + f"?project_uuid={self.project_uuid}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apps_count_by_project(self):
        response = self.request.get(self.url + f"?project_uuid={self.project_uuid}")
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
        response = self.request.get(
            self.url + f"?project_uuid={self.project_uuid}" + "&configured=true"
        )
        for app in response.json:
            self.assertNotEqual(app["config"], {})

        self.assertEqual(len(response.json), 5)

    def test_configured_equal_false_filter(self):
        response = self.request.get(
            self.url + f"?project_uuid={self.project_uuid}" + "&configured=false"
        )
        for app in response.json:
            self.assertEqual(app["config"], {})

        self.assertEqual(len(response.json), 5)

    def test_configured_wrong_data(self):
        response = self.request.get(
            self.url + f"?project_uuid={self.project_uuid}" + "&configured=test"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json[0],
            "Expected a boolean param in configured, but recived `test`",
        )

    def test_request_without_authorization(self):
        self.user_authorization.delete()
        response = self.request.get(self.url + f"?project_uuid={self.project_uuid}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(ALLOW_CRM_ACCESS=True, CRM_EMAILS_LIST=["user@marketplace.ai"])
    def test_request_with_crm_authorization(self):
        self.user_authorization.delete()
        response = self.request.get(self.url + f"?project_uuid={self.project_uuid}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# --- PreverifiedPhoneNumber view and FacebookClient.get_preverified_numbers ---


class PreverifiedPhoneNumberViewTestCase(PermissionTestCaseMixin, APIBaseTestCase):
    url = "/commerce/preverified-phone-number"
    view_class = PreverifiedPhoneNumber

    @property
    def view(self):
        return self.view_class.as_view()

    def setUp(self):
        super().setUp()
        self.grant_permission(self.user, "can_communicate_internally")

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=300)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_200_with_empty_list_when_meta_returns_no_numbers(
        self, mock_client_class, mock_ttl, mock_cache_set, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.return_value = {"data": []}
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, {"data": []})
        mock_client.get_preverified_numbers.assert_called_once()

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=300)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_200_with_one_id_when_meta_returns_numbers(
        self, mock_client_class, mock_ttl, mock_cache_set, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.return_value = {
            "data": [{"id": "999888777", "phone_number": "5511999999999"}],
        }
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.json)
        self.assertEqual(len(response.json["data"]), 1)
        self.assertEqual(response.json["data"][0], "999888777")

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_429_when_meta_returns_rate_limit(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = CustomAPIException(
            detail={"error": {"message": "Application request limit reached"}},
            status_code=429,
        )
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("error", response.json)

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_500_when_meta_returns_internal_error(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = CustomAPIException(
            detail={"error": {"message": "An unexpected error occurred"}},
            status_code=500,
        )
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.json)

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_500_when_meta_returns_other_error(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = CustomAPIException(
            detail={"error": {"message": "Bad request"}},
            status_code=400,
        )
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.json)

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_500_on_unexpected_exception(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = ValueError("unexpected")
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json.get("error"), "Internal server error")

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get")
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=300)
    def test_uses_cached_list_and_excludes_already_chosen_ids(
        self, mock_ttl, mock_cache_set, mock_cache_get
    ):
        cached = {
            "data_list": [
                {"id": "111", "phone_number": "5511111111111"},
                {"id": "222", "phone_number": "5522222222222"},
            ],
            "chosen_ids": ["111"],
            "expires_at": None,
        }
        mock_cache_get.return_value = cached
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["data"], ["222"])
        mock_cache_set.assert_called_once()
        call_args = mock_cache_set.call_args
        self.assertIn("111", call_args[0][1]["chosen_ids"])
        self.assertIn("222", call_args[0][1]["chosen_ids"])

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get")
    def test_returns_200_empty_when_all_cached_numbers_already_chosen(
        self, mock_cache_get
    ):
        cached = {
            "data_list": [{"id": "111", "phone_number": "5511111111111"}],
            "chosen_ids": ["111"],
            "expires_at": None,
        }
        mock_cache_get.return_value = cached
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, {"data": []})

    def test_returns_403_without_can_communicate_internally_permission(self):
        self.clear_permissions(self.user)
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_500_with_error_dict_when_meta_detail_is_string(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = CustomAPIException(
            detail="Connection timeout",
            status_code=503,
        )
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json.get("error"), "Connection timeout")

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.FacebookClient")
    def test_returns_500_when_meta_detail_is_none(
        self, mock_client_class, mock_cache_get
    ):
        mock_client = Mock()
        mock_client.get_preverified_numbers.side_effect = CustomAPIException(
            detail=None,
            status_code=503,
        )
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(
            response.json.get("error"),
            "Failed to fetch preverified numbers from Meta",
        )

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get")
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=120)
    @patch("marketplace.applications.views.FacebookClient")
    def test_expired_cache_triggers_meta_fetch(
        self, mock_client_class, mock_ttl, mock_cache_set, mock_cache_get
    ):
        past = timezone.now() - timedelta(seconds=60)
        mock_cache_get.return_value = {
            "data_list": [{"id": "old", "phone_number": "5511"}],
            "chosen_ids": [],
            "expires_at": past,
        }
        mock_client = Mock()
        mock_client.get_preverified_numbers.return_value = {
            "data": [{"id": "new1", "phone_number": "5522"}],
        }
        mock_client_class.return_value = mock_client
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["data"], ["new1"])
        mock_client.get_preverified_numbers.assert_called_once()

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get")
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=200)
    def test_uses_remaining_ttl_when_updating_cache_after_choice(
        self, mock_ttl, mock_cache_set, mock_cache_get
    ):
        mock_cache_get.return_value = {
            "data_list": [
                {"id": "111", "phone_number": "5511111111111"},
                {"id": "222", "phone_number": "5522222222222"},
            ],
            "chosen_ids": [],
            "expires_at": None,
        }
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.json["data"][0], ("111", "222"))
        mock_cache_set.assert_called_once()
        call_kwargs = mock_cache_set.call_args[1]
        self.assertEqual(call_kwargs["timeout"], 200)

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456")
    @patch("marketplace.applications.views.cache.get", return_value=None)
    @patch("marketplace.applications.views.cache.set")
    @patch("marketplace.applications.views.cache.ttl", return_value=300)
    @patch("marketplace.clients.facebook.client.RequestClient.make_request")
    def test_view_calls_real_client_get_preverified_numbers(
        self, mock_make_request, mock_ttl, mock_cache_set, mock_cache_get
    ):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [{"id": "555", "phone_number": "5511555555555"}],
        }
        mock_make_request.return_value = mock_response
        response = self.request.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["data"], ["555"])
        mock_make_request.assert_called_once()
        call_url = mock_make_request.call_args[0][0]
        self.assertIn("preverified_numbers", call_url)


class FacebookClientGetPreverifiedNumbersTestCase(TestCase):
    """Tests for FacebookClient.get_preverified_numbers (BusinessMetaRequests)."""

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="123456789")
    @patch("marketplace.clients.facebook.client.RequestClient.make_request")
    def test_get_preverified_numbers_calls_meta_with_expected_params(
        self, mock_make_request
    ):
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "111", "phone_number": "5511999999999"},
                {"id": "222", "phone_number": "5522988888888"},
            ],
        }
        mock_make_request.return_value = mock_response
        client = FacebookClient(access_token="fake_token")
        result = client.get_preverified_numbers()
        self.assertEqual(result, {"data": mock_response.json.return_value["data"]})
        mock_make_request.assert_called_once()
        call_args, call_kwargs = mock_make_request.call_args
        url = call_args[0]
        self.assertEqual(call_kwargs["method"], "GET")
        self.assertIn("123456789", url)
        self.assertIn("preverified_numbers", url)
        self.assertEqual(call_kwargs["params"]["limit"], 100)
        self.assertEqual(call_kwargs["params"]["code_verification_status"], "VERIFIED")
        self.assertEqual(call_kwargs["params"]["availability_status"], "AVAILABLE")
        self.assertIn("Authorization", call_kwargs["headers"])
        self.assertIn("Content-Type", call_kwargs["headers"])

    @override_settings(WHATSAPP_BSP_BUSINESS_ID="999")
    @patch("marketplace.clients.facebook.client.RequestClient.make_request")
    def test_get_preverified_numbers_returns_empty_data_when_meta_returns_empty(
        self, mock_make_request
    ):
        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_make_request.return_value = mock_response
        client = FacebookClient(access_token="fake_token")
        result = client.get_preverified_numbers()
        self.assertEqual(result, {"data": []})
        mock_make_request.assert_called_once()
