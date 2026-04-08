import uuid
from unittest.mock import patch
from queue import Queue

from django.test import TestCase

from marketplace.services.vtex.dtos import APICredentials
from marketplace.services.vtex.generic_service import VtexServiceBase
from marketplace.services.vtex.private.products.service import (
    PrivateProductsService,
)
from marketplace.clients.vtex.client import VtexPrivateClient
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.facebook_product_dto import (
    FacebookProductDTO,
)
from marketplace.wpp_products.tasks import _build_api_credentials


FAKE_PRODUCT_DETAILS = {
    "Id": 12345,
    "SkuName": "Test Product SKU",
    "ProductDescription": "A great test product",
    "IsActive": True,
    "DetailUrl": "/test-product/p",
    "BrandName": "TestBrand",
    "ImageUrl": "https://img.example.com/product.jpg",
    "Images": [{"ImageUrl": "https://img.example.com/product.jpg"}],
    "ProductName": "Test Product",
}


class FakeVtexClient:
    """
    Fake VTEX client that mirrors the real client interface
    with deterministic responses. Works as a drop-in replacement
    for both VtexPrivateClient and VtexProxyClient.
    """

    def __init__(self, available=True):
        self.available = available
        self.calls = {
            "get_product_details": [],
            "pub_simulate_cart_for_seller": [],
            "simulate_cart_for_multiple_sellers": [],
            "get_product_specification": [],
        }

    def check_domain(self, domain):
        return True

    def is_valid_credentials(self, domain):
        return True

    def get_product_details(self, sku_id, domain):
        self.calls["get_product_details"].append({"sku_id": sku_id, "domain": domain})
        return FAKE_PRODUCT_DETAILS

    def pub_simulate_cart_for_seller(
        self, sku_id, seller_id, domain, sales_channel=None
    ):
        self.calls["pub_simulate_cart_for_seller"].append(
            {
                "sku_id": sku_id,
                "seller_id": seller_id,
                "domain": domain,
                "sales_channel": sales_channel,
            }
        )
        if not self.available:
            return {
                "is_available": False,
                "price": 0,
                "list_price": 0,
                "selling_price": 0,
                "data": {},
            }
        return {
            "is_available": True,
            "price": 2990,
            "list_price": 3990,
            "selling_price": 2990,
            "data": {
                "items": [
                    {
                        "availability": "available",
                        "price": 2990,
                        "listPrice": 3990,
                        "sellingPrice": 2990,
                    }
                ]
            },
        }

    def simulate_cart_for_multiple_sellers(
        self, sku_id, sellers, domain, sales_channel=None
    ):
        self.calls["simulate_cart_for_multiple_sellers"].append(
            {
                "sku_id": sku_id,
                "sellers": sellers,
                "domain": domain,
                "sales_channel": sales_channel,
            }
        )
        results = {}
        for seller in sellers:
            if not self.available:
                results[seller] = {
                    "is_available": False,
                    "price": 0,
                    "list_price": 0,
                    "selling_price": 0,
                    "data": {},
                }
            else:
                results[seller] = {
                    "is_available": True,
                    "price": 2990,
                    "list_price": 3990,
                    "selling_price": 2990,
                    "data": {},
                }
        return results

    def get_product_specification(self, product_id, domain):
        self.calls["get_product_specification"].append(
            {"product_id": product_id, "domain": domain}
        )
        return []

    def list_all_products_sku_ids(self, domain, page_size=100000, sales_channel=None):
        return ["12345"]

    def list_active_sellers(self, domain, sales_channel=None):
        return ["seller1"]


class FakeSKUValidator:
    """
    Fake SKU validator that bypasses Redis/DB and returns
    product details directly from the service.
    """

    def __init__(self, service, domain, zeroshot_client):
        self.service = service

    def validate_product_details(self, sku_id, catalog):
        return self.service.get_product_details(sku_id, "fake-domain")


class FakeCatalog:
    """Fake catalog matching the real Catalog model interface."""

    def __init__(self, extra_config=None):
        config = {"rules": [], "store_domain": "www.teststore.com"}
        if extra_config:
            config.update(extra_config)
        self.vtex_app = type(
            "FakeApp",
            (),
            {
                "config": config,
                "uuid": uuid.uuid4(),
            },
        )()


class TestAPICredentials(TestCase):
    def test_v1_to_dict(self):
        creds = APICredentials(
            domain="store.vtex.com",
            app_key="key123",
            app_token="token456",
        )
        result = creds.to_dict()
        self.assertEqual(result["domain"], "store.vtex.com")
        self.assertEqual(result["app_key"], "key123")
        self.assertNotIn("use_io_proxy", result)

    def test_v2_to_dict(self):
        project = str(uuid.uuid4())
        creds = APICredentials(
            domain="store.vtex.com",
            use_io_proxy=True,
            project_uuid=project,
        )
        result = creds.to_dict()
        self.assertTrue(result["use_io_proxy"])
        self.assertEqual(result["project_uuid"], project)
        self.assertNotIn("app_key", result)


class TestBuildApiCredentials(TestCase):
    def test_builds_v1(self):
        result = _build_api_credentials(
            {
                "domain": "s.vtex.com",
                "app_key": "k",
                "app_token": "t",
            }
        )
        self.assertFalse(result.use_io_proxy)
        self.assertEqual(result.app_key, "k")

    def test_builds_v2(self):
        project = str(uuid.uuid4())
        result = _build_api_credentials(
            {
                "domain": "s.vtex.com",
                "use_io_proxy": True,
                "project_uuid": project,
            }
        )
        self.assertTrue(result.use_io_proxy)
        self.assertEqual(result.project_uuid, project)
        self.assertEqual(result.app_key, "")


class TestVtexServiceBaseFactory(TestCase):
    def setUp(self):
        self.service = VtexServiceBase()

    def test_create_client_v1(self):
        creds = APICredentials(domain="s.vtex.com", app_key="key", app_token="token")
        client = self.service._create_vtex_client(creds)
        self.assertIsInstance(client, VtexPrivateClient)

    @patch("marketplace.services.vtex.generic_service.VtexProxyClient")
    def test_create_client_v2(self, mock_proxy_cls):
        project = str(uuid.uuid4())
        creds = APICredentials(
            domain="s.vtex.com",
            use_io_proxy=True,
            project_uuid=project,
        )
        self.service._create_vtex_client(creds)
        mock_proxy_cls.assert_called_once_with(project_uuid=project)

    def test_private_service_v1(self):
        creds = APICredentials(domain="s.vtex.com", app_key="key", app_token="token")
        svc = self.service.get_private_service_for_credentials(creds)
        self.assertIsInstance(svc, PrivateProductsService)
        self.assertIsInstance(svc.client, VtexPrivateClient)

    def test_private_service_caches(self):
        creds = APICredentials(domain="s.vtex.com", app_key="key", app_token="token")
        self.assertIs(
            self.service.get_private_service_for_credentials(creds),
            self.service.get_private_service_for_credentials(creds),
        )

    def test_check_credentials_skips_for_proxy(self):
        creds = APICredentials(
            domain="s.vtex.com",
            use_io_proxy=True,
            project_uuid="abc",
        )
        self.assertTrue(self.service.check_is_valid_credentials(creds))


class TestDataProcessorWithProxy(TestCase):
    """
    End-to-end tests using FakeVtexClient and FakeSKUValidator.
    No MagicMock, no patch on data — only the SKUValidator class
    is swapped because it's hardcoded inside ProductProcessor.__init__.
    """

    SKU_VALIDATOR_PATH = "marketplace.services.vtex.utils.data_processor.SKUValidator"

    def _run(self, client, catalog, **kwargs):
        service = PrivateProductsService(client)
        dp = DataProcessor(queue=Queue(), use_threads=False, batch_size=100)
        with patch(self.SKU_VALIDATOR_PATH, FakeSKUValidator):
            return dp.process(
                catalog=catalog,
                domain="store.vtex.com",
                service=service,
                rules=[],
                store_domain="www.teststore.com",
                **kwargs,
            )

    def test_seller_sku_mode(self):
        client = FakeVtexClient(available=True)
        result = self._run(
            client,
            FakeCatalog(),
            items=["seller1#12345"],
            update_product=True,
            mode="seller_sku",
            priority=2,
        )

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], FacebookProductDTO)
        self.assertEqual(result[0].id, 12345)
        self.assertEqual(result[0].availability, "in stock")
        self.assertEqual(result[0].brand, "TestBrand")

        calls = client.calls["pub_simulate_cart_for_seller"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["sku_id"], "12345")
        self.assertEqual(calls[0]["seller_id"], "seller1")
        self.assertEqual(calls[0]["domain"], "store.vtex.com")

    def test_single_mode(self):
        client = FakeVtexClient(available=True)
        result = self._run(
            client,
            FakeCatalog({"use_sku_sellers": False}),
            items=["12345"],
            update_product=False,
            mode="single",
            sellers=["seller1"],
            priority=2,
        )

        self.assertEqual(len(result), 1)

        calls = client.calls["simulate_cart_for_multiple_sellers"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["sku_id"], "12345")
        self.assertEqual(calls[0]["sellers"], ["seller1"])

    def test_unavailable_skipped_when_not_updating(self):
        client = FakeVtexClient(available=False)
        result = self._run(
            client,
            FakeCatalog(),
            items=["seller1#12345"],
            update_product=False,
            mode="seller_sku",
            priority=2,
        )

        self.assertEqual(len(result), 0)

    def test_unavailable_included_when_updating(self):
        client = FakeVtexClient(available=False)
        result = self._run(
            client,
            FakeCatalog(),
            items=["seller1#12345"],
            update_product=True,
            mode="seller_sku",
            priority=2,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].availability, "out of stock")
        self.assertEqual(result[0].status, "archived")
