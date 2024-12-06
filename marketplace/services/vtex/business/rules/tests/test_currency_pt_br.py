from django.test import TestCase

from marketplace.services.vtex.business.rules.currency_pt_br import CurrencyBRL
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyPT_BR(TestCase):
    def setUp(self):
        self.rule = CurrencyBRL()

    def test_format_pt_br_price(self):
        product = FacebookProductDTO(
            id="test_pt_br",
            title="Produto em PT_BR",
            description="Preço em reais",
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

        self.assertEqual(product.price, "24.39 BRL")
        self.assertEqual(product.sale_price, "24.39 BRL")
