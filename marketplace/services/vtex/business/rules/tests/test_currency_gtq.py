from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_gtq import CurrencyGTQ
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyGTQ(TestCase):
    def setUp(self):
        self.rule = CurrencyGTQ()

    def test_format_gtq_price(self):
        product = FacebookProductDTO(
            id="test_gtq",
            title="Produto em GTQ",
            description="Preço em quetzais guatemaltecos",
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

        self.assertEqual(product.price, "24.39 GTQ")
        self.assertEqual(product.sale_price, "24.39 GTQ")
