import uuid

from unittest.mock import patch, PropertyMock
from rest_framework import status

from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.core.types.channels.whatsapp_cloud.catalogs.views.views import (
    CatalogViewSet,
)
from marketplace.applications.models import App
from marketplace.accounts.models import ProjectAuthorization
from marketplace.wpp_products.models import Catalog


class MockFacebookService:
    def __init__(self, *args, **kwargs):
        pass

    def enable_catalog(self, catalog):
        return {"success": "True"}

    def disable_catalog(self, catalog):
        return {"success": "True"}

    def get_connected_catalog(self, app):
        return "0123456789"


class SetUpTestBase(APIBaseTestCase):
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


class CatalogListTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "list"}

    def test_list_catalogs(self):
        url = reverse("catalog-list", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json["results"]), 1)

    def test_filter_by_name(self):
        url = reverse("catalog-list", kwargs={"app_uuid": self.app.uuid})

        response = self.client.get(url, {"name": "catalog test"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(len(response.json()["results"]), 0)

        response = self.client.get(url, {"name": "non-existing name"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)


class CatalogRetrieveTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "retrieve"}

    def test_retreive_catalog(self):
        url = reverse(
            "catalog-detail",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.get(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json), 5)


class CatalogEnabledTestCase(MockServiceTestCase):
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
        self.assertEqual(response.json["success"], "True")


class CatalogDisableTestCase(MockServiceTestCase):
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
        self.assertEqual(response.json["success"], "True")


class CatalogConnectedTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "list"}

    def test_list_catalog_with_connected_catalog(self):
        Catalog.objects.create(
            app=self.app,
            facebook_catalog_id="9876543210",
            name="another catalog test",
            category="commerce",
        )
        url = reverse("catalog-list", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json["results"]), 2)
        self.assertTrue(response.json["results"][0]["is_connected"])
