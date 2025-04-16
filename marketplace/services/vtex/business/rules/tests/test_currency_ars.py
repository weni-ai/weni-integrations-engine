from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_ars import CurrencyARS
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyARS(TestCase):
    def setUp(self):
        self.rule = CurrencyARS()

    def test_format_ars_price(self):
        product = FacebookProductDTO(
            id="test_ars",
            title="Produto em ARS",
            description="Preço em pesos argentinos",
            availability="in stock",
            status="active",
            condition="new",
            price=11250000,
            sale_price=8335000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "112500 ARS")
        self.assertEqual(product.sale_price, "83350 ARS")

    def test_format_ars_price_none(self):
        product = FacebookProductDTO(
            id="test_ars_none",
            title="Produto em ARS",
            description="Preço em pesos argentinos",
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

        self.assertEqual(product.price, "0 ARS")
        self.assertEqual(product.sale_price, "0 ARS")

    def test_format_ars_price_less_than_one(self):
        product = FacebookProductDTO(
            id="test_ars_lt_one",
            title="Produto em ARS",
            description="Preço em pesos argentinos",
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

        self.assertEqual(product.price, "1 ARS")
        self.assertEqual(product.sale_price, "1 ARS")

    def test_format_ars_price_zero(self):
        product = FacebookProductDTO(
            id="test_ars_zero",
            title="Produto em ARS",
            description="Preço em pesos argentinos",
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

        self.assertEqual(product.price, "0 ARS")
        self.assertEqual(product.sale_price, "0 ARS")

    def test_format_ars_price_exact_thousands(self):
        product = FacebookProductDTO(
            id="test_ars_exact",
            title="Produto em ARS",
            description="Preço em pesos argentinos",
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

        self.assertEqual(product.price, "10000 ARS")
        self.assertEqual(product.sale_price, "20000 ARS")

    def test_format_ars_price_large_values(self):
        product = FacebookProductDTO(
            id="test_ars_large",
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

        self.assertEqual(product.price, "10000000 ARS")
        self.assertEqual(product.sale_price, "21474836 ARS")
