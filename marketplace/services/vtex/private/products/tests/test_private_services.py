from django.test import TestCase
from unittest.mock import Mock, patch

from marketplace.services.vtex.business.rules.exclude_alcoholic_drinks import (
    ExcludeAlcoholicDrinks,
)
from marketplace.services.vtex.exceptions import CredentialsValidationError
from marketplace.services.vtex.private.products.service import PrivateProductsService


class MockClient:
    def is_valid_credentials(self, domain):
        return domain == "valid.domain.com"

    def check_domain(self, domain):
        return domain in ["valid.domain.com", "another.valid.com"]

    def list_active_sellers(self, domain):
        return ["seller1", "seller2"] if domain == "valid.domain.com" else []

    def list_all_products_sku_ids(self, domain):
        return ["sku1", "sku2"] if domain == "valid.domain.com" else []

    def get_product_details(self, sku_id, domain):
        return (
            {"sku_id": sku_id, "domain": domain} if domain == "valid.domain.com" else {}
        )

    def pub_simulate_cart_for_seller(
        self, sku_id, seller_id, domain, salles_channel=None
    ):
        return {"sku_id": sku_id, "seller_id": seller_id, "domain": domain}

    def get_product_specification(self, product_id, domain):
        return (
            {"product_id": product_id, "specification": "details"}
            if domain == "valid.domain.com"
            else {}
        )

    def simulate_cart_for_multiple_sellers(self, sku_id, sellers, domain):
        results = {}
        for seller in sellers:
            results[seller] = {
                "is_available": True,
                "price": 100,
                "list_price": 120,
                "data": {"items": [{"id": sku_id, "seller": seller}]},
            }
        return results


class MockCatalog:
    class VtexApp:
        def __init__(self, config):
            self.config = config

    def __init__(self, config, uuid):
        self.vtex_app = self.VtexApp(config)
        self.uuid = uuid


class PrivateProductsServiceTestCase(TestCase):
    def setUp(self):
        self.mock_client = MockClient()
        self.service = PrivateProductsService(self.mock_client)
        self.mock_catalog = MockCatalog(
            config={"rules": [], "store_domain": "store.domain.com"}, uuid="mock-uuid"
        )

    def test_check_is_valid_domain_valid(self):
        self.assertTrue(self.service.check_is_valid_domain("valid.domain.com"))

    def test_check_is_valid_domain_invalid(self):
        with self.assertRaises(CredentialsValidationError):
            self.service.check_is_valid_domain("invalid.domain.com")

    def test_validate_private_credentials_valid(self):
        self.assertTrue(self.service.validate_private_credentials("valid.domain.com"))

    def test_validate_private_credentials_invalid_domain(self):
        with self.assertRaises(CredentialsValidationError):
            self.service.validate_private_credentials("invalid.domain.com")

    def test_validate_private_credentials_invalid_credentials(self):
        self.mock_client.is_valid_credentials = Mock(return_value=False)
        result = self.service.validate_private_credentials("valid.domain.com")
        self.assertFalse(result)

    def test_list_active_sellers(self):
        sellers = self.service.list_active_sellers("valid.domain.com")
        self.assertEqual(sellers, ["seller1", "seller2"])

    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    def test_list_all_skus_ids(self, mock_cache_set, mock_cache_get):
        mock_cache_get.return_value = ["sku1", "sku2"]
        skus = self.service.list_all_skus_ids("valid.domain.com")
        mock_cache_get.assert_called_once_with("active_products_valid.domain.com")
        self.assertEqual(skus, ["sku1", "sku2"])

        mock_cache_get.return_value = None
        self.mock_client.list_all_products_sku_ids = Mock(return_value=["sku3", "sku4"])
        skus = self.service.list_all_skus_ids("new.domain.com")
        mock_cache_set.assert_called_once_with(
            "active_products_new.domain.com", ["sku3", "sku4"], timeout=36000
        )

    def test_get_product_details(self):
        details = self.service.get_product_details("sku1", "valid.domain.com")
        self.assertEqual(details, {"sku_id": "sku1", "domain": "valid.domain.com"})

    def test_simulate_cart_for_seller(self):
        cart = self.service.simulate_cart_for_seller(
            "sku1", "seller1", "valid.domain.com"
        )
        self.assertEqual(
            cart,
            {"sku_id": "sku1", "seller_id": "seller1", "domain": "valid.domain.com"},
        )

    def test_get_product_specification(self):
        specification = self.service.get_product_specification(
            "product1", "valid.domain.com"
        )
        self.assertEqual(
            specification, {"product_id": "product1", "specification": "details"}
        )

    def test_load_rules(self):
        rule_name_valid = "exclude_alcoholic_drinks"
        rule_name_invalid = "invalid_rule"

        rule_names = [rule_name_valid, rule_name_invalid]

        rules = self.service._load_rules(rule_names)

        # Check that the valid rule is loaded correctly
        self.assertEqual(len(rules), 1)
        self.assertIsInstance(rules[0], ExcludeAlcoholicDrinks)

        # Check that the invalid rule is not added
        for rule in rules:
            self.assertNotEqual(type(rule).__name__, "invalid_rule")

    def test_simulate_cart_for_multiple_sellers(self):
        sellers = ["seller1", "seller2"]
        results = self.service.simulate_cart_for_multiple_sellers(
            "sku1", sellers, "valid.domain.com"
        )

        self.assertEqual(len(results), 2)
        self.assertIn("seller1", results)
        self.assertIn("seller2", results)
        self.assertTrue(results["seller1"]["is_available"])
        self.assertEqual(results["seller1"]["price"], 100)
