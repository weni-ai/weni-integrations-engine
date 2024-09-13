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
from marketplace.wpp_products.models import Catalog, Product, ProductFeed


class MockFacebookService:
    def __init__(self, *args, **kwargs):
        pass

    def create_vtex_catalog(self, validated_data, app, vtex_app, user):
        if validated_data["name"] == "valid_catalog":
            return (Catalog(app=app, facebook_catalog_id="123456789"), "123456789")
        else:
            return (None, None)

    def catalog_deletion(self, catalog):
        if catalog.facebook_catalog_id == "123456789":
            return True
        else:
            return False

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
        self.catalog_success = Catalog.objects.create(
            app=self.app,
            facebook_catalog_id="123456789",
            name="valid_catalog",
            category="commerce",
        )
        self.catalog_failure = Catalog.objects.create(
            app=self.app,
            facebook_catalog_id="987654321",
            name="invlid_catalog",
            category="commerce",
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.product_feed = ProductFeed.objects.create(
            facebook_feed_id="050505050505",
            name="product_feed",
            catalog=self.catalog,
            created_by=self.user,
        )

        self.product = Product.objects.create(
            facebook_product_id="0202020202",
            title="Refrigerator",
            description="A FrostFree that works",
            availability="in stock",
            condition="new",
            price="9.99 USD",
            link="https://myproduct.com",
            image_link="https://myimage.com",
            brand="Mybrand",
            sale_price="919.99 USD",
            catalog=self.catalog,
            feed=self.product_feed,
            created_by=self.user,
        )

        self.product2 = Product.objects.create(
            facebook_product_id="0303030303",
            title="Monitor",
            description="A Game monitor that works",
            availability="out of stock",
            condition="new",
            price="200.90 USD",
            link="https://myproduct.com",
            image_link="https://myimage.com",
            brand="Mybrand",
            sale_price="200.90 USD",
            catalog=self.catalog,
            feed=self.product_feed,
            created_by=self.user,
        )

    @property
    def view(self):
        return self.view_class.as_view(self.current_view_mapping)


class MockServiceTestCase(SetUpTestBase):
    def setUp(self):
        super().setUp()
        # Mock Celery Task
        self.mock_celery_task = patch("marketplace.celery.app.send_task")
        self.mock_celery_task.start()
        self.addCleanup(self.mock_celery_task.stop)

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


# TODO: Fix the tests
# class CatalogListTestCase(MockServiceTestCase):
#     current_view_mapping = {"get": "list"}

#     def test_list_catalogs(self):
#         url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})
#         response = self.request.get(url, app_uuid=self.app.uuid)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.json["results"]), 3)

#     def test_filter_by_name(self):
#         url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})

#         response = self.client.get(url, {"name": "catalog test"})
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertNotEqual(len(response.json()["results"]), 0)

#         response = self.client.get(url, {"name": "non-existing name"})
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response.json()["results"]), 0)


class CatalogRetrieveTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "retrieve"}

    def test_retreive_catalog(self):
        url = reverse(
            "catalog-detail-delete",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.get(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json), 5)


# class CatalogEnabledTestCase(MockServiceTestCase):
#     current_view_mapping = {"post": "enable_catalog"}

#     def test_enable_catalog(self):
#         url = reverse(
#             "catalog-enable",
#             kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
#         )
#         response = self.request.post(
#             url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

# def test_failed_enable_catalog(self):
#     mock_facebook_service = MockFailiedEnableDisableCatalogFacebookService()
#     patcher_fb_failure = patch.object(
#         self.view_class,
#         "fb_service",
#         Mock(return_value=mock_facebook_service),
#     )
#     patcher_fb_failure.start()
#     self.addCleanup(patcher_fb_failure.stop)

#     url = reverse(
#         "catalog-enable",
#         kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
#     )
#     response = self.request.post(
#         url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
#     )
#     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# class CatalogDisableTestCase(MockServiceTestCase):
#     current_view_mapping = {"post": "disable_catalog"}

#     def test_disable_catalog(self):
#         url = reverse(
#             "catalog-disable",
#             kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
#         )
#         response = self.request.post(
#             url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
#         )
#         self.assertEqual(response.status_code, status.HTTP_200_OK)

# def test_failed_disable_catalog(self):
#     mock_facebook_service = MockFailiedEnableDisableCatalogFacebookService()
#     patcher_fb_failure = patch.object(
#         self.view_class,
#         "fb_service",
#         Mock(return_value=mock_facebook_service),
#     )
#     patcher_fb_failure.start()
#     self.addCleanup(patcher_fb_failure.stop)

#     url = reverse(
#         "catalog-disable",
#         kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
#     )
#     response = self.request.post(
#         url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
#     )
#     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CatalogConnectedTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "list"}

    def test_list_catalog_with_connected_catalog(self):
        Catalog.objects.create(
            app=self.app,
            facebook_catalog_id="9876543210",
            name="another catalog test",
            category="commerce",
        )
        url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})
        response = self.request.get(url, app_uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json["results"]), 4)
        self.assertTrue(response.json["results"][0]["is_connected"])


class CatalogDestroyTestCase(MockServiceTestCase):
    current_view_mapping = {"delete": "destroy"}

    def test_delete_catalog_success(self):
        url = reverse(
            "catalog-detail-delete",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )

        response = self.request.delete(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog_success.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_catalog_failure(self):
        url = reverse(
            "catalog-detail-delete",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.delete(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog_failure.uuid
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Failed to delete catalog on Facebook."
        )


class CatalogCreateTestCase(MockServiceTestCase):
    current_view_mapping = {"post": "create"}

    def setUp(self):
        super().setUp()
        # Configures a vtex App for an already created wpp-cloud App
        self.vtex_app_configured = App.objects.create(
            code="vtex",
            created_by=self.user,
            config={"domain": "valid_domain"},
            configured=True,
            project_uuid=self.app.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )
        # Creation of a wpp-cloud App to simulate a link with two Vtex Apps
        self.app_double_vtex = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        # Create a Vtex App 01 and 02 with repeating the project_uuid to simulate duplicity of integration
        self.vtex_app_01 = App.objects.create(
            code="vtex",
            created_by=self.user,
            config={"domain": "double_domain"},
            configured=True,
            project_uuid=self.app_double_vtex.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )
        self.vtex_app_02 = App.objects.create(
            code="vtex",
            created_by=self.user,
            config={"domain": "double_domain"},
            configured=True,
            project_uuid=self.app_double_vtex.project_uuid,
            platform=App.PLATFORM_WENI_FLOWS,
        )
        # Create a wpp-cloud without App-vtex linked to the project
        self.app_without_vtex = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

    # def test_create_catalog_with_vtex_app(self):
    #     data = {"name": "valid_catalog"}
    #     url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})

    #     response = self.request.post(url, data, app_uuid=self.app.uuid)
    #     self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    #     self.assertEqual(response.data["facebook_catalog_id"], "123456789")

    # def test_create_catalog_with_unconfigured_app(self):
    #     data = {"name": "valid_catalog"}
    #     url = reverse(
    #         "catalog-list-create", kwargs={"app_uuid": self.app_without_vtex.uuid}
    #     )

    #     response = self.request.post(url, data, app_uuid=self.app_without_vtex.uuid)
    #     self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    #     self.assertEqual(response.data["detail"], "There is no VTEX App configured.")

    # def test_create_catalog_with_multiple_configured_apps(self):
    #     data = {"name": "valid_catalog"}
    #     url = reverse(
    #         "catalog-list-create", kwargs={"app_uuid": self.app_double_vtex.uuid}
    #     )

    #     response = self.request.post(url, data, app_uuid=self.app_double_vtex.uuid)
    #     self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(
    #         response.data["detail"],
    #         "Multiple VTEX Apps are configured, which is not expected.",
    #     )

    # def test_create_catalog_failure(self):
    #     with patch.object(
    #         MockFacebookService, "create_vtex_catalog", return_value=(None, None)
    #     ):
    #         data = {"name": "valid_catalog"}
    #         url = reverse("catalog-list-create", kwargs={"app_uuid": self.app.uuid})

    #         response = self.request.post(url, data, app_uuid=self.app.uuid)
    #         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    #         self.assertEqual(
    #             response.data["detail"], "Failed to create catalog on Facebook."
    #         )


class CatalogListProductsTestCase(MockServiceTestCase):
    current_view_mapping = {"get": "list_products"}

    def test_list_catalog_products(self):
        url = reverse(
            "catalog-list-products",
            kwargs={"app_uuid": self.app.uuid, "catalog_uuid": self.catalog.uuid},
        )
        response = self.request.get(
            url, app_uuid=self.app.uuid, catalog_uuid=self.catalog.uuid
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json["results"]), 2)
