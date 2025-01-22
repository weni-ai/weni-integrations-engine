from django.test import TestCase
from marketplace.services.vtex.business.rules.round_up_calculate_by_weight import (
    RoundUpCalculateByWeight,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestRoundUpCalculateByWeight(TestCase):
    def setUp(self):
        self.rule = RoundUpCalculateByWeight()

    def test_apply_rounding_up_product_1(self):
        # Test a product that qualifies for rounding and weight calculation
        product = FacebookProductDTO(
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
                "UnitMultiplier": 0.5,
                "Dimension": {"weight": 1000.0},
                "ProductCategories": {"1": "carnes e aves"},
            },
        )
        expected_title = "Batata Doce Yakon Embalada Unidade"
        expected_description = (
            "Batata Doce Yakon Embalada - Aprox. 500g, Preço do KG: R$ 24.40"
        )
        expected_price = 1220

        self.rule.apply(product)

        self.assertEqual(product.title, expected_title)
        self.assertEqual(product.description, expected_description)
        self.assertEqual(product.price, expected_price)
        self.assertEqual(product.sale_price, expected_price)

    def test_not_apply_rule(self):
        # Test a product that should not have the rule applied
        product = FacebookProductDTO(
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
        )

        self.rule.apply(product)

        self.assertEqual(product.title, "Iogurte Natural")
        self.assertEqual(product.description, "Iogurte Natural 1L")
        self.assertEqual(product.price, 450)
        self.assertEqual(product.sale_price, 450)

    def test_calculates_by_weight_description_ends_with_unit(self):
        # Test product description ending with a unit indicator to exclude by weight calculation
        product = FacebookProductDTO(
            id="test4",
            title="Arroz",
            description="Arroz Integral 1kg",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product4",
            image_link="http://example.com/image4.jpg",
            brand="TestBrand",
            product_details={"ProductCategories": {"1": "hortifruti"}},
        )
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_calculates_by_weight_category_exclusion(self):
        # Test for exclusion if category is "iogurte"
        product = FacebookProductDTO(
            id="test5",
            title="Produto Y",
            description="Produto sem peso",
            availability="in stock",
            status="active",
            condition="new",
            price=1500,
            sale_price=1500,
            link="http://example.com/product5",
            image_link="http://example.com/image5.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"1": "iogurte"},
                "Dimension": {"weight": 500},
            },
        )
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_calculates_by_weight_title_ends_with_unit_indicator(self):
        # Product with title ending in "kg" should not qualify for weight calculation
        product = FacebookProductDTO(
            id="test6",
            title="Product 1kg",
            description="Product description",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"ProductCategories": {"1": "hortifruti"}},
        )
        self.assertFalse(self.rule._calculates_by_weight(product))

    def test_format_grams_under_one_kg(self):
        # Test gram formatting for values under 1 kg
        grams = self.rule._format_grams(0.5)
        self.assertEqual(grams, "500g")

    def test_format_grams_500_0000(self):
        grams = self.rule._format_grams(500.0000)
        self.assertEqual(grams, "500g")

    def test_format_grams_1000_0000(self):
        # Test gram formatting for 1 kg
        grams = self.rule._format_grams(1000.0000)
        self.assertEqual(grams, "1.000g")

    def test_format_grams_10000_0000(self):
        # Test gram formatting for 10 kg
        grams = self.rule._format_grams(10000.0000)
        self.assertEqual(grams, "10.000g")
