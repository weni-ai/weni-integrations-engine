import uuid

from unittest.mock import Mock, patch
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
        return True, {"success": "True"}

    def disable_catalog(self, catalog):
        return True, {"success": "True"}

    def get_connected_catalog(self, app):
        return "0123456789"


class MockFailiedEnableDisableCatalogFacebookService:
    def __init__(self, *args, **kwargs):
        pass

    def enable_catalog(self, catalog):
        return False, {"success": False}

    def disable_catalog(self, catalog):
        return False, {"success": False}


class MockFlowsService:
    def __init__(self, *args, **kwargs):
        pass

    def update_catalog_to_active(self, app, fba_catalog_id):
        pass

    def update_catalog_to_inactive(self, app, fba_catalog_id):
        pass


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

        # Mock Facebook service
        mock_facebook_service = MockFacebookService()
        patcher_fb = patch.object(
            self.view_class,
            "fb_service",
            Mock(return_value=mock_facebook_service),
        )
        self.addCleanup(patcher_fb.stop)
        patcher_fb.start()

        # Mock Flows service
        mock_flows_service = MockFlowsService()
        patcher_flows = patch.object(
            self.view_class,
            "flows_service",
            Mock(return_value=mock_flows_service),
        )
        self.addCleanup(patcher_flows.stop)
        patcher_flows.start()


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

    def test_failed_enable_catalog(self):
        mock_facebook_service = MockFailiedEnableDisableCatalogFacebookService()
        patcher_fb_failure = patch.object(
            self.view_class,
            "fb_service",
            Mock(return_value=mock_facebook_service),
        )
        patcher_fb_failure.start()
        self.addCleanup(patcher_fb_failure.stop)

        url = reverse(
            "catalog-enable",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.post(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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

    def test_failed_disable_catalog(self):
        mock_facebook_service = MockFailiedEnableDisableCatalogFacebookService()
        patcher_fb_failure = patch.object(
            self.view_class,
            "fb_service",
            Mock(return_value=mock_facebook_service),
        )
        patcher_fb_failure.start()
        self.addCleanup(patcher_fb_failure.stop)

        url = reverse(
            "catalog-disable",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.post(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
