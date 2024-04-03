import uuid

from unittest.mock import Mock, patch

from django.urls import reverse

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.webhooks.vtex.product_updates import VtexProductUpdateWebhook
from marketplace.applications.models import App


class MockWebhookQueueManager:
    def __init__(self, app_uuid, processing_product=False):
        self.app_uuid = app_uuid
        self.processing_product = processing_product

    def enqueue_webhook_data(self, sku_id, data):
        pass

    def is_processing_locked(self):
        return self.processing_product


class SetUpTestBase(APIBaseTestCase):
    view_class = VtexProductUpdateWebhook

    def setUp(self):
        super().setUp()
        api_credentials = {
            "domain": "valid_domain",
            "app_key": "valid_key",
            "app_token": "valid_token",
        }
        rules = [
            "calculate_by_weight",
            "currency_pt_br",
            "exclude_alcoholic_drinks",
            "unifies_id_with_seller",
        ]
        config = {
            "api_credentials": api_credentials,
            "initial_sync_completed": True,
            "rules": rules,
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

        # Mock Celery send_task
        patcher_celery = patch("marketplace.celery.app.send_task")
        self.mock_send_task = patcher_celery.start()
        self.addCleanup(patcher_celery.stop)

        # Mock Webhook manager
        mock_webhook_manager = MockWebhookQueueManager("1", "2")
        patcher_fb = patch.object(
            self.view_class,
            "get_queue_manager",
            Mock(return_value=mock_webhook_manager),
        )
        self.addCleanup(patcher_fb.stop)
        patcher_fb.start()


class WebhookTestCase(MockServiceTestCase):
    def test_request_ok(self):
        response = self.request.post(self.url, self.body, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, 200)

    def test_webhook_with_valid_configuration(self):
        self.app.config["initial_sync_completed"] = True
        self.app.save()

        response = self.request.post(self.url, self.body, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, 200)

    def test_webhook_without_initial_sync(self):
        self.app.config["initial_sync_completed"] = False
        self.app.save()

        response = self.request.post(self.url, self.body, app_uuid=self.app.uuid)
        self.assertEqual(response.status_code, 400)

    def test_webhook_with_app_not_found(self):
        app_uuid = uuid.uuid4()
        url = reverse("vtex-product-updates", kwargs={"app_uuid": uuid.uuid4()})
        response = self.request.post(url, self.body, app_uuid=app_uuid)
        self.assertEqual(response.status_code, 404)

    def test_webhook_with_processing_product(self):
        mock_webhook_manager = MockWebhookQueueManager("1", processing_product=True)

        with patch.object(
            self.view_class, "get_queue_manager", return_value=mock_webhook_manager
        ):
            response = self.request.post(self.url, self.body, app_uuid=self.app.uuid)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {"message": "Webhook product update added to the processing queue"},
        )
