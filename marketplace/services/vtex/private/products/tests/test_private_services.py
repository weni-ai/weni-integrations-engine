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

    def list_all_active_products(self, domain):
        return ["sku1", "sku2"] if domain == "valid.domain.com" else []

    def get_product_details(self, sku_id, domain):
        return (
            {"sku_id": sku_id, "domain": domain} if domain == "valid.domain.com" else {}
        )

    def pub_simulate_cart_for_seller(self, sku_id, seller_id, domain):
        return {"sku_id": sku_id, "seller_id": seller_id, "domain": domain}

    def get_product_specification(self, product_id, domain):
        return (
            {"product_id": product_id, "specification": "details"}
            if domain == "valid.domain.com"
            else {}
        )


class MockCatalog:
    class VtexApp:
        def __init__(self, config):
            self.config = config

    def __init__(self, config):
        self.vtex_app = self.VtexApp(config)


class PrivateProductsServiceTestCase(TestCase):
    def setUp(self):
        self.mock_client = MockClient()
        self.service = PrivateProductsService(self.mock_client)
        self.mock_catalog = MockCatalog(
            config={"rules": [], "store_domain": "store.domain.com"}
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

    def test_list_all_active_products(self):
        products = self.service.list_all_active_products("valid.domain.com")
        self.assertEqual(products, ["sku1", "sku2"])

    def test_list_all_products(self):
        self.service.data_processor.process_product_data = Mock(return_value=[])
        products = self.service.list_all_products("valid.domain.com", self.mock_catalog)
        self.assertIsInstance(products, list)

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

    def test_update_webhook_product_info(self):
        self.service.data_processor.process_product_data = Mock(return_value=[])
        updated_products = self.service.update_webhook_product_info(
            "valid.domain.com", ["sku1"], ["seller1"], self.mock_catalog
        )
        self.assertIsInstance(updated_products, list)

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

    def test_list_all_products_with_invalid_sellers(self):
        sellers = ["seller1", "invalid_seller"]
        self.service.list_active_sellers = Mock(return_value=["seller1", "seller2"])
        self.service.list_all_active_products = Mock(return_value=["sku1", "sku2"])
        self.service.data_processor.process_product_data = Mock(return_value=[])

        with patch("builtins.print") as mock_print:
            products = self.service.list_all_products(
                "valid.domain.com", self.mock_catalog, sellers
            )
            mock_print.assert_called_with(
                "Warning: Sellers IDs {'invalid_seller'} are not active and will be ignored."
            )
        self.assertIsInstance(products, list)
        self.service.data_processor.process_product_data.assert_called_once()
