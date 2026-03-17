from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_eur import CurrencyEUR
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyEUR(TestCase):
    def setUp(self):
        self.rule = CurrencyEUR()

    def test_format_eur_price(self):
        product = FacebookProductDTO(
            id="test_eur",
            title="Product in EUR",
            description="Price in euros",
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

        self.assertEqual(product.price, "24.39 EUR")
        self.assertEqual(product.sale_price, "24.39 EUR")
