import uuid

from unittest.mock import patch
from unittest.mock import Mock, MagicMock
from unittest.mock import PropertyMock

from django.urls import reverse

from rest_framework import status
from rest_framework.exceptions import APIException

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.accounts.models import ProjectAuthorization
from marketplace.applications.models import App
from marketplace.core.types.ecommerce.vtex.views import (
    VtexIntegrationDetailsView,
    VtexViewSet,
)
from marketplace.core.types.ecommerce.vtex.type import VtexType
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.vtex.app_manager import AppVtexManager
from marketplace.wpp_products.utils import SellerSyncUtils
from marketplace.core.types.ecommerce.vtex.usecases.create_vtex_integration import (
    CreateVtexIntegrationUseCase,
)
from marketplace.core.types.ecommerce.vtex.publisher.vtex_app_created_publisher import (
    VtexAppCreatedPublisher,
)
from marketplace.services.flows.service import FlowsService

apptype = VtexType()


class MockVtexService:
    def check_is_valid_credentials(self, credentials):
        return True

    def configure(self, app, credentials, wpp_cloud_uuid, store_domain):
        app.config["operator_token"] = credentials.to_dict()
        app.config["wpp_cloud_uuid"] = wpp_cloud_uuid
        app.config["store_domain"] = store_domain
        app.configured = True
        app.save()
        return app

    def active_sellers(self, app):
        return ["1", "2", "3", "4", "5"]

    def synchronized_sellers(self, app, sellers_id, sync_all_sellers=False):
        return True


class MockFlowsService:
    def update_vtex_integration_status(self, project_uuid, user_email, action):
        return True

    def update_vtex_ads_status(self, project_uuid, user_email, action):
        return True


class SetUpService(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()

        # Mock vtex service
        self.mock_service = MockVtexService()
        patcher = patch.object(
            self.view_class,
            "service",
            new_callable=PropertyMock,
            return_value=self.mock_service,
        )
        self.addCleanup(patcher.stop)
        patcher.start()

        # Mock FlowsClient
        self.mock_flows_client = Mock(spec=FlowsClient)
        self.mock_flows_service = MockFlowsService()
        self.mock_flows_service.flows_client = self.mock_flows_client

        patcher_flows = patch.object(
            self.view_class,
            "flows_service",
            PropertyMock(return_value=self.mock_flows_service),
        )
        self.addCleanup(patcher_flows.stop)
        patcher_flows.start()

        # Mock AppVtexManager
        self.mock_app_manager = Mock(spec=AppVtexManager)
        patcher_app_manager = patch.object(
            self.view_class,
            "app_manager",
            new_callable=PropertyMock,
            return_value=self.mock_app_manager,
        )
        self.addCleanup(patcher_app_manager.stop)
        patcher_app_manager.start()


class CreateVtexAppTestCase(SetUpService):
    url = reverse("vtex-app-list")

    def setUp(self):
        super().setUp()

        self.project_uuid = str(uuid.uuid4())
        self.body = {
            "project_uuid": self.project_uuid,
            "account": "store",
            "store_type": "type",
        }
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

        self.mock_flows_service = MagicMock(spec=FlowsService)
        self.mock_publisher = MagicMock(spec=VtexAppCreatedPublisher)

        self.mock_flows_service.update_vtex_integration_status.return_value = True
        self.mock_publisher.create_event.return_value = True

        self.use_case_patcher = patch(
            "marketplace.core.types.ecommerce.vtex.views.CreateVtexIntegrationUseCase",
            autospec=True,
        )
        self.MockUseCase = self.use_case_patcher.start()

        self.mock_use_case = MagicMock(spec=CreateVtexIntegrationUseCase)
        self.MockUseCase.return_value = self.mock_use_case

        self.mock_use_case.configure_app.side_effect = lambda app, data: app
        self.mock_use_case.notify_flows.return_value = True
        self.mock_use_case.publish_to_queue.return_value = None

        self.flows_service_patcher = patch(
            "marketplace.core.types.ecommerce.vtex.views.FlowsService",
            return_value=self.mock_flows_service,
        )
        self.flows_service_mock = self.flows_service_patcher.start()

        self.publisher_patcher = patch(
            "marketplace.core.types.ecommerce.vtex.views.VtexAppCreatedPublisher",
            return_value=self.mock_publisher,
        )
        self.publisher_mock = self.publisher_patcher.start()

    def tearDown(self):
        super().tearDown()
        self.use_case_patcher.stop()
        self.flows_service_patcher.stop()
        self.publisher_patcher.stop()

    def test_request_ok(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_CREATE)

    def test_create_app_without_project_uuid(self):
        self.body.pop("project_uuid")
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_app_platform(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.json["platform"], App.PLATFORM_VTEX)

    def test_create_app_with_no_app(self):
        with patch.object(self.view_class, "get_app", return_value=None):
            response = self.request.post(self.url, self.body)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            self.mock_use_case.configure_app.assert_not_called()
            self.mock_use_case.notify_flows.assert_not_called()
            self.mock_use_case.publish_to_queue.assert_not_called()

    def test_notify_flows_called(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.mock_use_case.notify_flows.assert_called_once()

    def test_publish_to_queue_called(self):
        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.mock_use_case.publish_to_queue.assert_called_once()

    def test_publish_to_queue_failure(self):
        self.mock_use_case.publish_to_queue.side_effect = APIException(
            detail={"error": "Failed to publish Vtex app creation."}
        )

        response = self.request.post(self.url, self.body)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class RetrieveVtexAppTestCase(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()

        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-detail", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_RETRIEVE)

    def test_request_ok(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_app_data(self):
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertIn("uuid", response.json)
        self.assertIn("project_uuid", response.json)
        self.assertIn("platform", response.json)
        self.assertIn("created_on", response.json)
        self.assertEqual(response.json["config"], {})


class DeleteVtexAppTestCase(SetUpService):
    view_class = VtexViewSet

    @property
    def view(self):
        return self.view_class.as_view(APIBaseTestCase.ACTION_DESTROY)

    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-detail", kwargs={"uuid": self.app.uuid})

    def test_delete_app_plataform(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())

    def test_delete_app_with_wrong_project_uuid(self):
        response = self.request.delete(self.url, uuid=str(uuid.uuid4()))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_app_without_autorization(self):
        self.user_authorization.set_role(ProjectAuthorization.ROLE_NOT_SETTED)
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_release_ecommerce_service(self):
        response = self.request.delete(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(App.objects.filter(uuid=self.app.uuid).exists())


class GetAppUUIDTestCase(SetUpService):
    def setUp(self):
        super().setUp()
        self.url = reverse("vtex-app-get-app-uuid")

    @property
    def view(self):
        return self.view_class.as_view({"get": "get_app_uuid"})

    def test_get_app_uuid(self):
        with patch.object(
            self.view_class.app_manager,
            "get_vtex_app_uuid",
            return_value=str(uuid.uuid4()),
        ):
            response = self.request.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn("uuid", response.data)


class SyncSellersTestCase(SetUpService):
    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-sync-sellers", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"post": "sync_sellers"})

    def test_sync_sellers_success(self):
        sellers = ["1", "2", "3", "4", "5"]
        body = {"sellers": sellers, "project_uuid": self.app.project_uuid}
        response = self.request.post(self.url, body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sync_all_sellers_success(self):
        body = {"sync_all_sellers": True, "project_uuid": self.app.project_uuid}
        response = self.request.post(self.url, body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sync_sellers_failure(self):
        sellers = ["1", "2", "3", "4", "5"]
        body = {"sellers": sellers, "project_uuid": self.app.project_uuid}
        with patch.object(
            self.view_class.service, "synchronized_sellers", return_value=False
        ):
            response = self.request.post(self.url, body, uuid=self.app.uuid)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("message", response.data)
            self.assertEqual(
                response.data["message"], "failure to start synchronization"
            )

    def test_sync_sellers_with_both_params(self):
        sellers = ["1", "2", "3"]
        body = {
            "sellers": sellers,
            "sync_all_sellers": True,
            "project_uuid": self.app.project_uuid,
        }
        response = self.request.post(self.url, body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.json)
        self.assertEqual(
            response.json["non_field_errors"],
            [
                "Cannot provide both 'sellers' list and 'sync_all_sellers' at the same time."
            ],
        )


class ActiveSellersTestCase(SetUpService):
    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)
        self.url = reverse("vtex-app-active-sellers", kwargs={"uuid": self.app.uuid})

    @property
    def view(self):
        return self.view_class.as_view({"get": "active_sellers"})

    def test_active_sellers(self):
        response_data = ["1", "2", "3", "4", "5"]
        response = self.request.get(self.url, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response_data)


class VtexViewSetTestCase(APIBaseTestCase):
    view_class = VtexViewSet

    def setUp(self):
        super().setUp()
        self.project_uuid = str(uuid.uuid4())
        self.app = App.objects.create(
            code="vtex",
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_VTEX,
        )
        self.url = reverse("vtex-app-check-sync-status", kwargs={"uuid": self.app.uuid})
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.project_uuid, role=ProjectAuthorization.ROLE_CONTRIBUTOR
        )

    @property
    def view(self):
        return self.view_class.as_view({"get": "check_sync_status"})

    @patch.object(SellerSyncUtils, "get_lock_data")
    def test_check_sync_status_in_progress(self, mock_get_lock_data):
        mock_get_lock_data.return_value = {"start_time": "2023-06-27T12:00:00Z"}

        response = self.request.get(self.url, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            response.data["message"], "A synchronization is already in progress"
        )
        self.assertIn("data", response.data)

    @patch.object(SellerSyncUtils, "get_lock_data")
    def test_check_sync_status_not_in_progress(self, mock_get_lock_data):
        mock_get_lock_data.return_value = None

        response = self.request.get(self.url, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "No synchronization in progress")


class UpdateVtexAdsTestCase(SetUpService):
    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.url = reverse("vtex-app-update-vtex-ads", kwargs={"uuid": self.app.uuid})
        self.body = {
            "vtex_ads": True,
            "project_uuid": self.app.project_uuid,
        }
        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid, role=ProjectAuthorization.ROLE_ADMIN
        )

    @property
    def view(self):
        return self.view_class.as_view({"post": "update_vtex_ads"})

    def test_update_vtex_ads_success(self):
        response = self.request.post(self.url, self.body, uuid=self.app.uuid)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.mock_app_manager.update_vtex_ads.assert_called_once_with(
            self.app, self.body["vtex_ads"]
        )


class VtexIntegrationDetailsViewTest(APIBaseTestCase):
    view_class = VtexIntegrationDetailsView

    def setUp(self):
        super().setUp()
        self.project_uuid = uuid.uuid4()
        self.url = reverse(
            "integration-details", kwargs={"project_uuid": self.project_uuid}
        )

        self.vtex_app = App.objects.create(
            code="vtex",
            created_by=self.user,
            project_uuid=self.project_uuid,
            platform=App.PLATFORM_VTEX,
            config={
                "operator_token": {
                    "app_key": "key123",
                    "app_token": "token123",
                    "domain": "vtex.com",
                }
            },
        )

    def test_integration_details_success(self):
        response = self.request.get(self.url, project_uuid=self.project_uuid)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("app_key", response.data)
        self.assertIn("app_token", response.data)
        self.assertIn("domain", response.data)

    def test_integration_details_not_found(self):
        invalid_project_uuid = uuid.uuid4()
        url = reverse(
            "integration-details", kwargs={"project_uuid": invalid_project_uuid}
        )
        response = self.request.get(url, project_uuid=invalid_project_uuid)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @property
    def view(self):
        """
        Overriding the 'view' property of the base class.
        Returns the view that will be used in the test.
        """
        return self.view_class.as_view()


class LinkCatalogTestCase(SetUpService):
    def setUp(self):
        super().setUp()
        self.app = apptype.create_app(
            created_by=self.user, project_uuid=str(uuid.uuid4())
        )
        self.wpp_cloud_app = App.objects.create(
            code="wpp-cloud", created_by=self.user, project_uuid=self.app.project_uuid
        )

        self.user_authorization = self.user.authorizations.create(
            project_uuid=self.app.project_uuid
        )
        self.user_authorization.set_role(ProjectAuthorization.ROLE_ADMIN)

        self.url = reverse("vtex-app-link-catalog", kwargs={"uuid": self.app.uuid})
        self.body = {
            "catalog_id": "catalog123",
            "domain": "test.vtex.com",
            "store_domain": "store.vtex.com",
            "app_key": "test_app_key",
            "app_token": "test_app_token",
            "wpp_cloud_uuid": str(self.wpp_cloud_app.uuid),
            "project_uuid": self.app.project_uuid,
        }

    @property
    def view(self):
        return self.view_class.as_view({"post": "link_catalog"})

    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.link_catalog_start_sync.LinkCatalogAndStartSyncUseCase.link_catalog",  # noqa: E501
        return_value=True,
    )
    def test_link_catalog_success(self, mock_link_catalog):
        # Fazer a requisição
        response = self.request.post(self.url, self.body, uuid=self.app.uuid)

        # Verificar a resposta
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json["message"],
            "Catalog linked and synchronization task dispatched successfully",
        )

        # Verificar que o método foi chamado corretamente
        mock_link_catalog.assert_called_once_with(catalog_id=self.body["catalog_id"])

    @patch(
        "marketplace.core.types.ecommerce.vtex.usecases.link_catalog_start_sync.LinkCatalogAndStartSyncUseCase"
    )
    def test_link_catalog_failure(self, mock_use_case_class):
        mock_use_case_instance = Mock()
        mock_use_case_instance.link_catalog.return_value = False
        mock_use_case_class.return_value = mock_use_case_instance

        response = self.request.post(self.url, self.body, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json["error"],
            "Failed to link catalog and start product synchronization",
        )

    def test_link_catalog_invalid_data(self):
        invalid_body = self.body.copy()
        invalid_body.pop("catalog_id")

        response = self.request.post(self.url, invalid_body, uuid=self.app.uuid)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("catalog_id", response.json)

    def test_link_catalog_app_not_found(self):
        invalid_url = reverse(
            "vtex-app-link-catalog", kwargs={"uuid": str(uuid.uuid4())}
        )

        with patch.object(
            self.view_class, "get_object", side_effect=Exception("App not found")
        ):
            response = self.request.post(invalid_url, self.body)

            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.json["error"], "VTEX app not found")
