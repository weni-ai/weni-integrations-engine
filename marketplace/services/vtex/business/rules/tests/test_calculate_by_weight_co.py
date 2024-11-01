from django.test import TestCase
from marketplace.services.vtex.business.rules.calculate_by_weight_co import (
    CalculateByWeightCO,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCalculateByWeightCO(TestCase):
    def setUp(self):
        self.rule = CalculateByWeightCO()

    def test_apply_with_increase(self):
        # Test for category eligible for 10% increase
        product = FacebookProductDTO(
            id="test3",
            title="Carne molida de cordero Majada",
            description="Disfruta todos los mejores productos que tiene Majada para ti",
            availability="in stock",
            status="Active",
            condition="new",
            price=1164000,
            sale_price=1164000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="Majada",
            product_details={
                "UnitMultiplier": 1.0,
                "Dimension": {"weight": 500.0000},
                "ProductCategories": {"1": "carne y pollo"},
            },
        )
        expected_price = product.price * 1.10

        self.rule.apply(product)

        self.assertAlmostEqual(product.price, expected_price, places=1)
        self.assertAlmostEqual(product.sale_price, expected_price, places=1)

    def test_apply_without_increase(self):
        # Test for a category not eligible for a price increase
        product = FacebookProductDTO(
            id="test4",
            title="Produto Comum",
            description="Produto comum sem categoria específica",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="GenericBrand",
            product_details={
                "UnitMultiplier": 1.0,
                "Dimension": {"weight": 400.0},
                "ProductCategories": {"1": "outra categoria"},
            },
        )
        expected_price = product.price

        self.rule.apply(product)

        self.assertEqual(product.price, expected_price)
        self.assertEqual(product.sale_price, expected_price)

    def test_calculates_by_weight_with_title_ending(self):
        # Test for product title ending with a unit to exclude from weight calculation
        product = FacebookProductDTO(
            id="test5",
            title="Produto 500g",
            description="Descrição do Produto",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={
                "UnitMultiplier": 1.0,
                "Dimension": {"weight": 500},
                "ProductCategories": {"1": "frios e laticínios"},
            },
        )
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_calculates_by_weight_with_description_ending(self):
        # Test for product description ending with a unit to exclude from weight calculation
        product = FacebookProductDTO(
            id="test6",
            title="Produto Qualquer",
            description="Descrição do Produto 1kg",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            product_details={
                "UnitMultiplier": 1.0,
                "Dimension": {"weight": 1000},
                "ProductCategories": {"1": "padaria"},
            },
        )
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_format_grams(self):
        # Test formatting of weights in grams for different cases
        self.assertEqual(self.rule._format_grams(0.5), "500g")  # Less than 1 kg
        self.assertEqual(
            self.rule._format_grams(500.0), "500g"
        )  # Exact weight in grams
        self.assertEqual(self.rule._format_grams(1000.0), "1.000g")  # 1 kg
        self.assertEqual(self.rule._format_grams(10000.0), "10.000g")  # 10 kg

    def test_apply_without_multiplier_increase(self):
        # Test applying rule without 10% increase (category not eligible)
        product = FacebookProductDTO(
            id="test7",
            title="Produto Básico",
            description="Descrição de produto básico",
            availability="in stock",
            status="active",
            condition="new",
            price=2000,
            sale_price=2000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="BasicBrand",
            product_details={
                "UnitMultiplier": 1.0,
                "Dimension": {
                    "weight": 300.0000
                },  # Weight below threshold for increase
                "ProductCategories": {"1": "carne y pollo"},
            },
        )
        expected_price = product.price  # No increase applied

        self.rule.apply(product)

        self.assertEqual(product.price, expected_price)
        self.assertEqual(product.sale_price, expected_price)
