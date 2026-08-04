from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_ron import CurrencyRON
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyRON(TestCase):
    def setUp(self):
        self.rule = CurrencyRON()

    def test_format_ron_price(self):
        product = FacebookProductDTO(
            id="test_ron",
            title="Product in RON",
            description="Price in Romanian lei",
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

        self.assertEqual(product.price, "24.39 RON")
        self.assertEqual(product.sale_price, "24.39 RON")
