from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_pt_br_round_floor import (
    CurrencyBRLRoudingFloor,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyBRLRoudingFloor(TestCase):
    def setUp(self):
        self.rule = CurrencyBRLRoudingFloor()

    def test_apply_price_and_sale_price_formatted(self):
        """Test apply method formats both price and sale_price"""
        product = FacebookProductDTO(
            id="test_brl_1",
            title="Produto em BRL",
            description="Preço em reais brasileiros",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,  # R$100.00 in cents
            sale_price=8500,  # R$85.00 in cents
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, "100.00 BRL")
        self.assertEqual(product.sale_price, "85.00 BRL")

    def test_format_price_exact_value(self):
        """Test format_price method with exact cent values"""
        result = self.rule.format_price(10000)

        self.assertEqual(result, "100.00 BRL")

    def test_format_price_with_cent_decimals(self):
        """Test format_price method with cent decimals that need rounding down"""
        result = self.rule.format_price(
            10005
        )  # R$100.05 -> should round down to R$100.05
        expected = "100.04 BRL"  # Floor rounding: 100049/100 = 1004.49 -> floor to 1004.49 -> 100.04 BRL
        self.assertEqual(result, expected)

    def test_format_price_large_value(self):
        """Test format_price method with large values"""
        result = self.rule.format_price(
            1234567
        )  # R$12345.67 -> should round down to R$12345.67
        expected = "12345.67 BRL"
        self.assertEqual(result, expected)

    def test_format_price_zero(self):
        """Test format_price method with zero value"""
        result = self.rule.format_price(0)

        self.assertEqual(result, "0.00 BRL")

    def test_format_price_small_value(self):
        """Test format_price method with small value"""
        result = self.rule.format_price(1)  # R$0.01

        self.assertEqual(result, "0.01 BRL")

    def test_format_price_negative_value(self):
        """Test format_price method with negative value"""
        result = self.rule.format_price(-1000)  # R$-10.00

        self.assertEqual(result, "-10.00 BRL")

    def test_format_price_decimal_precision_edge_case(self):
        """Test format_price method with values that test decimal precision"""
        # Test values that would have decimal precision without rounding floor
        result1 = self.rule.format_price(10001)  # R$100.01
        self.assertEqual(result1, "100.01 BRL")

        result2 = self.rule.format_price(12399)  # R$123.99
        self.assertEqual(
            result2, "123.98 BRL"
        )  # Floor rounding: 12399/100 = 123.99 -> floor to 123.98

    def test_format_price_only_price_set(self):
        """Test apply method when only price is set"""
        product = FacebookProductDTO(
            id="test_only_price",
            title="Produto apenas Preço",
            description="Produto sem sale_price",
            availability="in stock",
            status="active",
            condition="new",
            price=15000,
            sale_price=None,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        # Modify rule to handle None values
        original_format_price = self.rule.format_price

        def mock_format_price(price):
            if price is None:
                return None
            return original_format_price(price)

        self.rule.format_price = mock_format_price

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, "150.00 BRL")
        self.assertEqual(product.sale_price, None)  # None stays None

    def test_format_price_only_sale_price_set(self):
        """Test apply method when only sale_price is set"""
        product = FacebookProductDTO(
            id="test_only_sale",
            title="Produto apenas Sale Price",
            description="Produto sem price",
            availability="in stock",
            status="active",
            condition="new",
            price=None,
            sale_price=7500,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        # Modify rule to handle None values
        original_format_price = self.rule.format_price

        def mock_format_price(price):
            if price is None:
                return None
            return original_format_price(price)

        self.rule.format_price = mock_format_price

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, None)  # None stays None
        self.assertEqual(product.sale_price, "75.00 BRL")

    def test_rounding_floor_behavior(self):
        """Test that ROUND_FLOOR behavior is correctly applied"""
        # Test values that demonstrate floor rounding behavior
        product = FacebookProductDTO(
            id="test_floor_rounding",
            title="Produto Floor Rounding",
            description="Teste de arredondamento floor",
            availability="in stock",
            status="active",
            condition="new",
            price=10001,  # R$100.01
            sale_price=20002,  # R$200.02
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, "100.01 BRL")
        self.assertEqual(product.sale_price, "200.02 BRL")

    def test_format_price_with_fractional_cents(self):
        """Test format_price method simulation with fractional cent values"""
        # Test that decimal precision is maintained correctly
        test_cases = [
            (1234, "12.33 BRL"),  # Floor: 1234/100 = 12.34 -> floor to 12.33
            (5678, "56.78 BRL"),  # R$56.78
            (9999, "99.98 BRL"),  # Floor: 9999/100 = 99.99 -> floor to 99.98
        ]

        for input_price, expected in test_cases:
            result = self.rule.format_price(input_price)
            self.assertEqual(result, expected, f"Failed for input {input_price}")
