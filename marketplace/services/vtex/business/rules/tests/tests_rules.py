import unittest

from marketplace.services.vtex.business.rules.round_up_calculate_by_weight import (
    RoundUpCalculateByWeight,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class MockProductsDTO(unittest.TestCase):
    def setUp(self):
        self.products = [
            FacebookProductDTO(
                id="test1",
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
                id="test2",
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
            FacebookProductDTO(
                id="test3",
                title="Produto 1000kg",
                description="Descrição do Produto",
                availability="in stock",
                status="active",
                condition="new",
                price=1000,
                link="http://example.com/product1",
                image_link="http://example.com/image1.jpg",
                brand="TestBrand",
                sale_price=1000,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1},
                    "ProductCategories": {"category": "padaria"},
                },
            ),
            FacebookProductDTO(
                id="test4",
                title="Produto",
                description="Descrição 1000ml",
                availability="in stock",
                status="active",
                condition="new",
                price=200,
                link="http://example.com/product2",
                image_link="http://example.com/image2.jpg",
                brand="TestBrand2",
                sale_price=200,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1},
                    "ProductCategories": {"category": "padaria"},
                },
            ),
            FacebookProductDTO(
                id="test5",
                title="Pequeno Produto",
                description="Peso menor que um kg",
                availability="in stock",
                status="active",
                condition="new",
                price=50,
                link="http://example.com/product3",
                image_link="http://example.com/image3.jpg",
                brand="TestBrand3",
                sale_price=50,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 0.5},
                    "ProductCategories": {"category": "hortifruti"},
                },
            ),
            FacebookProductDTO(
                id="test6",
                title="Grande Produto",
                description="Peso acima de um milhar",
                availability="in stock",
                status="active",
                condition="new",
                price=1050,
                link="http://example.com/product4",
                image_link="http://example.com/image4.jpg",
                brand="TestBrand4",
                sale_price=1050,
                product_details={
                    "UnitMultiplier": 1.0,
                    "Dimension": {"weight": 1050},
                    "ProductCategories": {"category": "hortifruti"},
                },
            ),
        ]


class TestRoundUpCalculateByWeight(MockProductsDTO):
    def setUp(self):
        super().setUp()  # Call setUp of MockProductsDTO
        self.rule = RoundUpCalculateByWeight()

    def test_apply_rounding_up_product_1(self):
        product = self.products[0]

        before_title = product.title
        expected_title = f"{before_title} Unidade"
        expected_price_per_kg = "24.40"

        _, weight = self.rule._get_product_measurements(product)
        grams = self.rule._format_grams(weight)
        expected_description = (
            f"{before_title} - Aprox. {grams}, Preço do KG: R$ {expected_price_per_kg}"
        )

        self.rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, 1464)
        self.assertEqual(product.sale_price, 1464)

    def test_not_apply_rule(self):
        product = self.products[1]

        before_title = product.title
        expected_title = f"{before_title}"
        before_description = product.description
        expected_description = before_description

        self.rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, 450)
        self.assertEqual(product.sale_price, 450)

    def test_title_ends_with_unit_indicator(self):
        product = self.products[2]
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_description_ends_with_unit_indicator(self):
        product = self.products[3]
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_weight_less_than_one_kg(self):
        product = self.products[4]
        weight = self.rule._get_weight(product)
        self.assertEqual(self.rule._format_grams(weight), "500g")

    def test_format_grams_above_thousand(self):
        product = self.products[5]
        weight = self.rule._get_weight(product)
        self.assertEqual(self.rule._format_grams(weight), "1.050g")
