from django.test import TestCase
from marketplace.services.vtex.business.rules.currency_co import CurrencyCOP
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCurrencyCOP(TestCase):
    def setUp(self):
        self.rule = CurrencyCOP()

    def test_format_cop_price(self):
        product = FacebookProductDTO(
            id="test_cop",
            title="Produto em COP",
            description="Preço em pesos colombianos",
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

        self.assertEqual(product.price, "24.39 COP")
        self.assertEqual(product.sale_price, "24.39 COP")
