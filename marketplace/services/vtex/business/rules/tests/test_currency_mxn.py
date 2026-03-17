from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_mxn import CurrencyMXN
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyMXN(TestCase):
    def setUp(self):
        self.rule = CurrencyMXN()

    def test_format_mxn_price(self):
        product = FacebookProductDTO(
            id="test_mxn",
            title="Product in MXN",
            description="Price in Mexican pesos",
            availability="in stock",
            status="active",
            condition="new",
            price=2439,
            sale_price=2439,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={},
        )

        self.rule.apply(product)

        self.assertEqual(product.price, "24.39 MXN")
        self.assertEqual(product.sale_price, "24.39 MXN")
