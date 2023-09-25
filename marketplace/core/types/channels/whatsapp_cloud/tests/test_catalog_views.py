import uuid

from unittest.mock import patch, Mock
from rest_framework import status
from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_cloud.views import CatalogViewSet
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.wpp_products.models import Catalog


class CatalogViewSetBaseTestCase(APIBaseTestCase):
    current_view_mapping = {}
    view_class = CatalogViewSet

    def setUp(self):
        super().setUp()

        self.app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.catalog = Catalog.objects.create(
            app=self.app,
            facebook_catalog_id="0123456789",
            name="catalog test",
            category="commerce",
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.fb_service_mock = self._create_mock_service()
        self.patcher = patch(
            "marketplace.core.types.channels.whatsapp_cloud.views.FacebookService",
            return_value=self.fb_service_mock,
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        super().tearDown()

    def _create_mock_service(self):
        mock_service = Mock()

        mock_service.enable_catalog.return_value = {"status": "enabled"}
        mock_service.disable_catalog.return_value = {"status": "disabled"}
        mock_service.wpp_commerce_settings.return_value = {"settings_status": "active"}
        mock_service.toggle_catalog_visibility.return_value = {
            "visibility_status": "visible"
        }
        mock_service.toggle_cart.return_value = {"cart_status": "visible"}
        mock_service.get_connected_catalog.return_value = (
            self.catalog.facebook_catalog_id
        )

        return mock_service

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)


class ListCatalogTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"get": "list"}

    def test_list_catalogs(self):
        url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json), 1)


class EnabledCatalogTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"post": "enable_catalog"}

    def test_enable_catalog(self):
        url = reverse(
            "catalog-enable",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.post(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["status"], "enabled")


class DisableCatalogTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"post": "disable_catalog"}

    def test_disable_catalog(self):
        url = reverse(
            "catalog-disable",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.post(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["status"], "disabled")


class CommerceSettingsCatalogTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"get": "commerce_settings_status"}

    def test_commerce_settings_status(self):
        url = reverse("commerce-settings-status", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["settings_status"], "active")


class ToggleCatalogVisibilityTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"post": "toggle_catalog_visibility"}

    def test_toggle_catalog_visibility(self):
        url = reverse("toggle-catalog-visibility", kwargs={"app_uuid": self.app.uuid})
        response = self.request.post(url, body={"enable": True}, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["visibility_status"], "visible")


class ToggleCartVisibilityTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"post": "toggle_cart_visibility"}

    def test_toggle_cart_visibility(self):
        url = reverse("toggle-cart-visibility", kwargs={"app_uuid": self.app.uuid})
        response = self.request.post(url, body={"enable": True}, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["cart_status"], "visible")


class GetActiveCatalogTestCase(CatalogViewSetBaseTestCase):
    current_view_mapping = {"get": "get_active_catalog"}

    def test_get_active_catalog(self):
        url = reverse("catalog-active", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json, self.catalog.facebook_catalog_id)
