from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from marketplace.clients.exceptions import CustomAPIException
from marketplace.services.facebook.service import FacebookService
from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.tests.fakes import (
    FakeFacebookCatalogClient,
    FakeVtexClient,
    VtexFakeTestCase,
    VtexTestEnvironment,
    build_sku_detail,
)
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.enums import ProductPriority


DOMAIN = "store.myvtex.com"


class FakeVtexClientTest(TestCase):
    """Contract tests for the in-memory VTEX fake."""

    def test_credentials_and_domain_flags(self):
        client = FakeVtexClient(domain_valid=False, credentials_valid=False)

        self.assertFalse(client.check_domain(DOMAIN))
        self.assertFalse(client.is_valid_credentials(DOMAIN))

    def test_lists_registered_sellers_and_skus(self):
        client = (
            FakeVtexClient()
            .add_product("1047", sellers=["1"])
            .add_product("2099", sellers=["1", "2"])
        )

        self.assertEqual(sorted(client.list_active_sellers(DOMAIN)), ["1", "2"])
        self.assertEqual(
            sorted(client.list_all_products_sku_ids(DOMAIN)), ["1047", "2099"]
        )

    def test_get_product_details_returns_vtex_shape(self):
        client = FakeVtexClient().add_product(
            "1047", name="Laranja Bahia", brand="Arado"
        )

        details = client.get_product_details("1047", DOMAIN)

        self.assertEqual(details["Id"], "1047")
        self.assertEqual(details["SkuName"], "Laranja Bahia")
        self.assertEqual(details["BrandName"], "Arado")
        self.assertTrue(details["IsActive"])
        self.assertEqual(details["SkuSellers"][0]["SellerId"], "1")

    def test_get_product_details_raises_404_for_unknown_sku(self):
        client = FakeVtexClient()

        with self.assertRaises(CustomAPIException) as ctx:
            client.get_product_details("404", DOMAIN)

        self.assertEqual(ctx.exception.status_code, 404)

    def test_simulate_cart_for_seller_available(self):
        client = FakeVtexClient().add_product(
            "1047", sellers=["1"], available=True, price=1500, selling_price=1200
        )

        result = client.pub_simulate_cart_for_seller("1047", "1", DOMAIN)

        self.assertTrue(result["is_available"])
        self.assertEqual(result["price"], 1500)
        self.assertEqual(result["selling_price"], 1200)
        self.assertIn("data", result)

    def test_simulate_cart_for_seller_unknown_returns_unavailable(self):
        client = FakeVtexClient()

        result = client.pub_simulate_cart_for_seller("999", "1", DOMAIN)

        self.assertEqual(result, {"is_available": False, "price": 0, "list_price": 0})

    def test_simulate_cart_for_multiple_sellers(self):
        client = FakeVtexClient().add_product(
            "1047", sellers=["1", "2"], available=True, price=1000
        )

        results = client.simulate_cart_for_multiple_sellers("1047", ["1", "2"], DOMAIN)

        self.assertEqual(set(results.keys()), {"1", "2"})
        self.assertTrue(results["1"]["is_available"])
        self.assertTrue(results["2"]["is_available"])

    def test_records_calls_as_spy(self):
        client = FakeVtexClient().add_product("1047")

        client.get_product_details("1047", DOMAIN)
        client.list_active_sellers(DOMAIN)

        recorded = [name for name, _ in client.calls]
        self.assertIn("get_product_details", recorded)
        self.assertIn("list_active_sellers", recorded)

    def test_build_sku_detail_defaults(self):
        detail = build_sku_detail("55", sellers=["7"])

        self.assertEqual(detail["Id"], "55")
        self.assertEqual(detail["SkuSellers"][0]["SellerId"], "7")
        self.assertTrue(detail["Images"][0]["ImageUrl"])


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vtex-fakes-service-tests",
        }
    }
)
class FakeVtexClientThroughServiceTest(TestCase):
    """The fake is faithful enough to drive the real PrivateProductsService."""

    def setUp(self):
        self.client = FakeVtexClient().add_product(
            "1047", sellers=["1"], available=True, price=1500
        )
        self.service = PrivateProductsService(self.client)

    def test_validate_private_credentials(self):
        self.assertTrue(self.service.validate_private_credentials(DOMAIN))

    def test_list_all_skus_ids_uses_client(self):
        self.assertEqual(self.service.list_all_skus_ids(DOMAIN), ["1047"])

    def test_simulate_cart_for_seller_passthrough(self):
        result = self.service.simulate_cart_for_seller("1047", "1", DOMAIN)

        self.assertTrue(result["is_available"])
        self.assertEqual(result["price"], 1500)


class VtexTestEnvironmentTest(TestCase):
    """The reusable environment wires DB fixtures + fakes consistently."""

    def test_create_wires_apps_catalog_and_service(self):
        env = VtexTestEnvironment.create()

        self.assertEqual(env.vtex_app.code, "vtex")
        self.assertEqual(env.wpp_cloud_app.code, "wpp-cloud")
        self.assertEqual(env.catalog.vtex_app, env.vtex_app)
        self.assertEqual(env.catalog.app, env.wpp_cloud_app)
        self.assertEqual(env.project_uuid, str(env.vtex_app.project_uuid))
        self.assertIsInstance(env.service, PrivateProductsService)

    def test_add_product_is_visible_through_service(self):
        env = VtexTestEnvironment.create().add_product("1047", price=1500)

        details = env.service.get_product_details("1047", env.domain)

        self.assertEqual(details["Id"], "1047")


class FakeFacebookCatalogClientTest(TestCase):
    """The Meta fake is faithful enough to drive the real FacebookService."""

    def test_upload_batch_returns_handles_and_records_items(self):
        client = FakeFacebookCatalogClient()
        service = FacebookService(client)
        payload = {
            "item_type": "PRODUCT_ITEM",
            "requests": [
                {"method": "UPDATE", "data": {"id": "1047#1", "title": "Laranja"}}
            ],
        }

        response = service.upload_batch("cat-123", payload)

        self.assertTrue(response["handles"])
        self.assertEqual(client.uploaded_items[0]["id"], "1047#1")
        self.assertEqual(client.calls[0][0], "upload_items_batch")


class FakeVtexClientDataProcessorTest(VtexFakeTestCase):
    """
    End-to-end: the environment feeds the real DataProcessor pipeline (API_ONLY
    mode), producing faithful FacebookProductDTOs without touching VTEX, the DB
    writes or redis.
    """

    def build_environment(self) -> VtexTestEnvironment:
        env = VtexTestEnvironment.create(store_domain="www.arado.com.br")
        env.add_product(
            "1047",
            sellers=["1"],
            available=True,
            price=1500,
            selling_price=1200,
            name="Laranja Bahia Importada",
            brand="Arado",
        )
        return env

    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    @patch(
        "marketplace.services.vtex.utils.sku_validator.get_redis_connection",
        return_value=MagicMock(),
    )
    def test_process_produces_faithful_dto(self, _mock_redis, _mock_close):
        processor = DataProcessor(use_threads=False)

        results = processor.process(
            items=["1047"],
            catalog=self.vtex.catalog,
            domain=self.vtex.domain,
            service=self.vtex.service,
            rules=[],
            store_domain=self.vtex.store_domain,
            mode="single",
            sellers=["1"],
            priority=ProductPriority.API_ONLY,
        )

        self.assertEqual(len(results), 1)
        dto = results[0]
        self.assertEqual(dto.id, "1047")
        self.assertEqual(dto.availability, "in stock")
        self.assertEqual(dto.brand, "Arado")
        self.assertEqual(dto.price, 1500)
        self.assertEqual(dto.sale_price, 1200)
        self.assertEqual(dto.link, "https://www.arado.com.br/1047/p?idsku=1047")

    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    @patch(
        "marketplace.services.vtex.utils.sku_validator.get_redis_connection",
        return_value=MagicMock(),
    )
    def test_process_skips_unavailable_product(self, _mock_redis, _mock_close):
        self.vtex.add_product("2099", sellers=["1"], available=False)
        processor = DataProcessor(use_threads=False)

        results = processor.process(
            items=["2099"],
            catalog=self.vtex.catalog,
            domain=self.vtex.domain,
            service=self.vtex.service,
            rules=[],
            store_domain=self.vtex.store_domain,
            mode="single",
            sellers=["1"],
            priority=ProductPriority.API_ONLY,
        )

        self.assertEqual(results, [])
