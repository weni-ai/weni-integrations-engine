import unittest


from marketplace.services.vtex.business.rules.round_up_calculate_by_weight import (
    RoundUpCalculateByWeight,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class MockProductsDTO(unittest.TestCase):
    def setUp(self):
        self.products = [
            FacebookProductDTO(
                id="12345",
                title="Batata Doce Yakon Embalada",
                description="Batata Doce Yakon Embalada",
                availability="in stock",
                status="active",
                condition="new",
                price=2439,
                link="http://example.com/product",
                image_link="http://example.com/product.jpg",
                brand="ExampleBrand",
                sale_price=2439,
                product_details={
                    "UnitMultiplier": 0.6,
                    "Dimension": {
                        "cubicweight": 0.3063,
                        "height": 5.0,
                        "length": 21.0,
                        "weight": 1000.0,
                        "width": 14.0,
                    },
                    "ProductCategories": {"1": "carnes e aves"},
                },
            ),
            FacebookProductDTO(
                id="54321",
                title="Iogurte Natural",
                description="Iogurte Natural 1L",
                availability="in stock",
                status="active",
                condition="new",
                price=450,
                link="http://example.com/yogurt",
                image_link="http://example.com/yogurt.jpg",
                brand="DairyBrand",
                sale_price=450,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1000},
                    "ProductCategories": {
                        "557": "Leite Fermentado",
                        "290": "Iogurte",
                        "220": "Frios e Laticínios",
                    },
                },
            ),
        ]


class TestRoundUpCalculateByWeight(MockProductsDTO):
    def test_apply_rounding_up_product_1(self):
        rule = RoundUpCalculateByWeight()
        product = self.products[0]

        before_title = product.title
        expected_title = f"{before_title} Unidade"
        expected_price_per_kg = "24.40"

        _, weight = rule._get_product_measurements(product)
        grams = rule._format_grams(weight)
        expected_description = (
            f"{before_title} - Aprox. {grams}, Preço do KG: R$ {expected_price_per_kg}"
        )

        rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, 1464)
        self.assertEqual(product.sale_price, 1464)

    def test_not_apply_rule(self):
        rule = RoundUpCalculateByWeight()
        product = self.products[1]

        before_title = product.title
        expected_title = f"{before_title}"
        before_description = product.description
        expected_description = before_description

        rule.apply(product)
        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, 450)
        self.assertEqual(product.sale_price, 450)
