import uuid

from django.urls import reverse
from unittest.mock import patch, PropertyMock
from rest_framework import status


from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_cloud.catalogs.views.views import (
    CommerceSettingsViewSet,
)
from marketplace.wpp_products.models import Catalog


class MockFacebookService:
    def __init__(self, *args, **kwargs):
        pass

    def wpp_commerce_settings(self, app):
        return {"settings_status": "active"}

    def toggle_catalog_visibility(self, app, visible):
        return {"visibility_status": "visible"}

    def toggle_cart(self, app, visible):
        return {"cart_status": "visible"}

    def get_connected_catalog(self, app):
        return "0123456789"


class SetUpTestBase(APIBaseTestCase):
    current_view_mapping = {}
    view_class = CommerceSettingsViewSet

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

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)


class MockServiceTestCase(SetUpTestBase):
    def setUp(self):
        super().setUp()

        # Mock service
        mock_service = MockFacebookService()
        patcher = patch.object(
            self.view_class, "fb_service", PropertyMock(return_value=mock_service)
        )
        self.addCleanup(patcher.stop)
        patcher.start()


class CommerceSettingsCatalogTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "commerce_settings_status"}

    def test_commerce_settings_status(self):
        url = reverse("commerce-settings-status", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["settings_status"], "active")


class CommerceSettingsToggleCatalogVisibilityTestCase(MockServiceTestCase):
    current_view_mapping = {"post": "toggle_catalog_visibility"}

    def test_toggle_catalog_visibility(self):
        url = reverse("toggle-catalog-visibility", kwargs={"app_uuid": self.app.uuid})
        response = self.request.post(url, body={"enable": True}, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["visibility_status"], "visible")


class CommerceSettingsToggleCartVisibilityTestCase(MockServiceTestCase):
    current_view_mapping = {"post": "toggle_cart_visibility"}

    def test_toggle_cart_visibility(self):
        url = reverse("toggle-cart-visibility", kwargs={"app_uuid": self.app.uuid})
        response = self.request.post(url, body={"enable": True}, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json["cart_status"], "visible")


class CommerceSettingsGetActiveCatalogTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "get_active_catalog"}

    def test_get_active_catalog(self):
        url = reverse("catalog-active", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, "0123456789")
