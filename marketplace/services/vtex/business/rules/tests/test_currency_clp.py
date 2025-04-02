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
            price=11299000,
            sale_price=8399000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "112.990 CLP")
        self.assertEqual(product.sale_price, "83.990 CLP")

    def test_format_clp_price_none(self):
        product = FacebookProductDTO(
            id="test_clp",
            title="Produto em CLP",
            description="Preço em pesos chilenos",
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

    def test_format_clp_price_less_than_one(self):
        product = FacebookProductDTO(
            id="test_clp_small",
            title="Produto com preço mínimo",
            description="Preço menor que 1 peso chileno",
            availability="in stock",
            status="active",
            condition="new",
            price=50,
            sale_price=25,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "0.50 CLP")
        self.assertEqual(product.sale_price, "0.25 CLP")

    def test_format_clp_price_zero(self):
        product = FacebookProductDTO(
            id="test_clp_zero",
            title="Produto gratuito",
            description="Preço zero",
            availability="in stock",
            status="active",
            condition="new",
            price=0,
            sale_price=0,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "0 CLP")
        self.assertEqual(product.sale_price, "0 CLP")

    def test_format_clp_price_exact_thousands(self):
        product = FacebookProductDTO(
            id="test_clp_exact",
            title="Produto com preço exato",
            description="Preço em valor exato de milhares",
            availability="in stock",
            status="active",
            condition="new",
            price=1000000,
            sale_price=2000000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "10.990 CLP")
        self.assertEqual(product.sale_price, "20.990 CLP")

    def test_format_clp_price_decimal_values(self):
        product = FacebookProductDTO(
            id="test_clp_decimal",
            title="Produto com preço decimal",
            description="Preço com valores decimais",
            availability="in stock",
            status="active",
            condition="new",
            price=1234567,
            sale_price=9876543,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "12.990 CLP")
        self.assertEqual(product.sale_price, "98.990 CLP")

    def test_format_clp_price_large_values(self):
        product = FacebookProductDTO(
            id="test_clp_large",
            title="Produto com preço alto",
            description="Preço com valor muito alto",
            availability="in stock",
            status="active",
            condition="new",
            price=1000000000,
            sale_price=2147483647,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "10000.990 CLP")
        self.assertEqual(product.sale_price, "21474.990 CLP")
