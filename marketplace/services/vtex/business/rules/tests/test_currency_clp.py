from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_clp import CurrencyCLP
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyCLP(TestCase):
    def setUp(self):
        self.rule = CurrencyCLP()

    def test_format_clp_price(self):
        product = FacebookProductDTO(
            id="test_clp",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
            availability="in stock",
            status="active",
            condition="new",
            price=25345,  # 253.45 units
            sale_price=10050,  # 100.50 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "253.990 CLP")  # 253.45 → 253 → 253.990
        self.assertEqual(product.sale_price, "100.990 CLP")  # 100.50 → 100 → 100.990

    def test_format_clp_price_with_zero_cents(self):
        product = FacebookProductDTO(
            id="test_clp_zero_cents",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
            availability="in stock",
            status="active",
            condition="new",
            price=25300,  # 253.00 units
            sale_price=10000,  # 100.00 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "253.990 CLP")  # 253.00 → 253 → 253.990
        self.assertEqual(product.sale_price, "100.990 CLP")  # 100.00 → 100 → 100.990

    def test_format_clp_price_with_small_values(self):
        product = FacebookProductDTO(
            id="test_clp_small_values",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
            availability="in stock",
            status="active",
            condition="new",
            price=99,  # 0.99 units
            sale_price=1,  # 0.01 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "1 CLP")  # 0.99 → 0 → 1 CLP
        self.assertEqual(product.sale_price, "1 CLP")  # 0.01 → 0 → 1 CLP

    def test_format_clp_price_with_large_values(self):
        product = FacebookProductDTO(
            id="test_clp_large_values",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
            availability="in stock",
            status="active",
            condition="new",
            price=1000000,  # 10000.00 units
            sale_price=9999999,  # 99999.99 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "10000.990 CLP")  # 10000.00 → 10000 → 10000.990
        self.assertEqual(
            product.sale_price, "99999.990 CLP"
        )  # 99999.99 → 99999 → 99999.990

    def test_format_clp_price_with_odd_values(self):
        product = FacebookProductDTO(
            id="test_clp_odd_values",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
            availability="in stock",
            status="active",
            condition="new",
            price=12350.87,  # 123.5087 units
            sale_price=67890,  # 678.90 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "123.990 CLP")  # 123.5087 → 123 → 123.990
        self.assertEqual(product.sale_price, "678.990 CLP")  # 678.90 → 678 → 678.990

    def test_format_clp_price_with_decimal_values(self):
        product = FacebookProductDTO(
            id="test_clp_decimal_values",
            title="Produto em CLP",
            description="Preço em pesos chilenos com decimais",
            availability="in stock",
            status="active",
            condition="new",
            price=12345.67,  # 123.4567 units
            sale_price=9876.54,  # 98.7654 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "123.990 CLP")  # 123.4567 → 123 → 123.990
        self.assertEqual(product.sale_price, "98.990 CLP")  # 98.7654 → 98 → 98.990

    def test_format_clp_price_with_rounding_edge_cases(self):
        product = FacebookProductDTO(
            id="test_clp_rounding_edge",
            title="Produto em CLP",
            description="Casos de borda para arredondamento",
            availability="in stock",
            status="active",
            condition="new",
            price=9999,  # 99.99 units
            sale_price=10001,  # 100.01 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "99.990 CLP")  # 99.99 → 99 → 99.990
        self.assertEqual(product.sale_price, "100.990 CLP")  # 100.01 → 100 → 100.990

    def test_format_clp_price_with_none_values(self):
        product = FacebookProductDTO(
            id="test_clp_none_values",
            title="Produto em CLP",
            description="Preços nulos",
            availability="in stock",
            status="active",
            condition="new",
            price=None,
            sale_price=None,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "0 CLP")
        self.assertEqual(product.sale_price, "0 CLP")

    def test_format_clp_price_with_very_large_values(self):
        product = FacebookProductDTO(
            id="test_clp_very_large_values",
            title="Produto em CLP",
            description="Preços muito grandes",
            availability="in stock",
            status="active",
            condition="new",
            price=1000000000,  # 10.000.000,00 units
            sale_price=999999999,  # 9.999.999,99 units
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(
            product.price, "10000000.990 CLP"
        )  # 10.000.000,00 → 10.000.000 → 10.000.000,990
        self.assertEqual(
            product.sale_price, "9999999.990 CLP"
        )  # 9.999.999,99 → 9.999.999 → 9.999.999,990
