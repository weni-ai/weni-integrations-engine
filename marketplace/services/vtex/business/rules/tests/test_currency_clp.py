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
