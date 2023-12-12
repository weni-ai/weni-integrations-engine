import uuid

from unittest.mock import patch

from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.webhooks.vtex.product_updates import VtexProductUpdateWebhook
from marketplace.applications.models import App


class MockVtexService:
    def update_product_info(self, domain, webhook_payload):
        return [{"id": 1, "sku": 1}, {"id": 2, "sku": 2}]


class MockFlowsService:
    def update_vtex_products(self, products):
        return None


class SetUpTestBase(APIBaseTestCase):
    view_class = VtexProductUpdateWebhook

    def setUp(self):
        super().setUp()
        api_credentials = {
            "domain": "valid_domain",
            "app_key": "valid_key",
            "app_token": "valid_token",
        }
        config = {
            "api_credentials": api_credentials,
            "initial_sync_completed": True,
        }
        self.app = App.objects.create(
            code="vtex",
            created_by=self.user,
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_VTEX,
            configured=True,
            config=config,
        )
        self.url = reverse("vtex-product-updates", kwargs={"app_uuid": self.app.uuid})

        self.body = {
            "IdSku": "15",
            "An": "prezunic.myvtex",
            "IdAffiliate": "SPT",
            "DateModified": "2023-08-20T15:11:28.1978783Z",
            "IsActive": False,
            "StockModified": False,
            "PriceModified": False,
            "HasStockKeepingUnitModified": True,
            "HasStockKeepingUnitRemovedFromAffiliate": False,
        }

    @property
    def view(self):
        return self.view_class.as_view()


class MockServiceTestCase(SetUpTestBase):
    def setUp(self):
        super().setUp()

        # Mock Vtex service
        self.mock_vtex_service = MockVtexService()
        patcher_vtex = patch.object(
            self.view_class,
            "vtex_service_class",
            lambda *args, **kwargs: self.mock_vtex_service,
        )
        self.addCleanup(patcher_vtex.stop)
        patcher_vtex.start()

        # Mock Flows service
        self.mock_flows_service = MockFlowsService()
        patcher_flows = patch.object(
            self.view_class,
            "flows_service_class",
            lambda *args, **kwargs: self.mock_flows_service,
        )
        self.addCleanup(patcher_flows.stop)
        patcher_flows.start()


class WebhookTestCase(MockServiceTestCase):
    def test_request_ok(self):
        response = self.request.post(self.url, self.body, app_uuid=self.app.uuid)
        print(response.data)
        self.assertEqual(response.status_code, 200)

    def test_webhook_with_valid_configuration(self):
        self.app.config["initial_sync_completed"] = True
        self.app.save()

        response = self.request.post(
            self.url, {"data": "webhook_payload"}, app_uuid=self.app.uuid
        )
        self.assertEqual(response.status_code, 200)

    def test_webhook_without_initial_sync(self):
        self.app.config["initial_sync_completed"] = False
        self.app.save()

        response = self.request.post(
            self.url, {"data": "webhook_payload"}, app_uuid=self.app.uuid
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_with_app_not_found(self):
        app_uuid = uuid.uuid4()
        url = reverse("vtex-product-updates", kwargs={"app_uuid": uuid.uuid4()})
        response = self.request.post(
            url, {"data": "webhook_payload"}, app_uuid=app_uuid
        )
        self.assertEqual(response.status_code, 404)

    def test_webhook_with_invalid_credentials(self):
        self.app.config["initial_sync_completed"] = True
        self.app.config["api_credentials"] = {
            "domain": "",
            "app_key": "",
            "app_token": "",
        }
        self.app.save()

        response = self.request.post(
            self.url, {"data": "webhook_payload"}, app_uuid=self.app.uuid
        )
        self.assertEqual(response.status_code, 400)
