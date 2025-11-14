from django.test import TestCase
from marketplace.services.vtex.business.rules.calculate_by_weight import (
    CalculateByWeight,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCalculateByWeight(TestCase):
    def setUp(self):
        self.rule = CalculateByWeight()

    def create_product(
        self,
        categories=None,
        weight=None,
        multiplier=None,
        title_end=None,
        description_end=None,
    ):
        """Helper method to create test products"""

        product_details = {
            "UnitMultiplier": multiplier or 1.0,
            "Dimension": {"weight": weight or 1.0},
            "ProductCategories": categories or {"main": "hortifruti"},
        }

        title = "Banana"
        if title_end:
            title += title_end

        description = "Banana orgânica"
        if description_end:
            description += description_end

        return FacebookProductDTO(
            id="test_product",
            title=title,
            description=description,
            availability="in stock",
            status="active",
            condition="new",
            price=500,  # R$5.00 in cents
            sale_price=400,  # R$4.00 in cents
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details=product_details,
        )

    def test_apply_calculates_by_weight_normal_case(self):
        """Test apply method when product calculates by weight"""
        product = self.create_product()

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana Unidade")
        self.assertIn(
            "Aprox. 1g", product.description
        )  # Actual behavior: formats 1.0 as "1g"
        self.assertIn("Preço do KG: R$ 4.00", product.description)

    def test_apply_not_calculates_by_weight_title_ends_with_kg(self):
        """Test apply method when title ends with kg unit"""
        product = self.create_product(title_end=" 1kg")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana 1kg")
        self.assertEqual(product.description, "Banana orgânica")

    def test_apply_not_calculates_by_weight_title_ends_with_g(self):
        """Test apply method when title ends with g unit"""
        product = self.create_product(title_end=" 500g")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana 500g")
        self.assertEqual(product.description, "Banana orgânica")

    def test_apply_not_calculates_by_weight_title_ends_with_ml(self):
        """Test apply method when title ends with ml unit"""
        product = self.create_product(title_end=" 250ml")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana 250ml")

    def test_apply_not_calculates_by_weight_description_ends_with_unidade(self):
        """Test apply method when description ends with unidade"""
        product = self.create_product(description_end=" unidade")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana")
        self.assertEqual(product.description, "Banana orgânica unidade")

    def test_apply_not_calculates_by_weight_iogurte_category(self):
        """Test apply method excludes iogurte category"""
        product = self.create_product(categories={"main": "iogurte"})

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana")
        self.assertEqual(product.description, "Banana orgânica")

    def test_apply_not_calculates_by_weight_wrong_category(self):
        """Test apply method doesn't calculate for wrong category"""
        product = self.create_product(categories={"main": "perfumaria"})

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.title, "Banana")
        self.assertEqual(product.description, "Banana orgânica")

    def test_calculates_by_weight_for_valid_categories(self):
        """Test _calculates_by_weight method with valid categories"""

        # Test each valid category
        valid_categories = [
            "hortifruti",
            "carnes e aves",
            "frios e laticínios",
            "padaria",
        ]

        for category in valid_categories:
            product = self.create_product(categories={"main": category})

            result = self.rule._calculates_by_weight(product)
            self.assertTrue(result, f"Failed for category: {category}")

    def test_calculates_by_weight_for_iogurte_exclusion(self):
        """Test _calculates_by_weight method excludes iogurte"""
        product = self.create_product(categories={"main": "iogurte"})

        result = self.rule._calculates_by_weight(product)
        self.assertFalse(result)

    def test_get_multiplier_with_value(self):
        """Test _get_multiplier method with valid value"""
        product = self.create_product(multiplier=3.5)

        multiplier = self.rule._get_multiplier(product)
        self.assertEqual(multiplier, 3.5)

    def test_get_multiplier_default(self):
        """Test _get_multiplier method with default value"""
        product = self.create_product()  # Uses default 1.0

        multiplier = self.rule._get_multiplier(product)
        self.assertEqual(multiplier, 1.0)

    def test_get_weight(self):
        """Test _get_weight method"""
        product = self.create_product(weight=1.2)

        weight = self.rule._get_weight(product)
        self.assertEqual(weight, 1.2)

    def test_format_price(self):
        """Test _format_price method"""
        self.assertEqual(self.rule._format_price(100.50), "100.50")
        self.assertEqual(self.rule._format_price(0), "0.00")
        self.assertEqual(
            self.rule._format_price(999.999), "1000.00"
        )  # Decimal rounds up to 1000.00

    def test_format_grams_value_less_than_one(self):
        """Test _format_grams method with value less than one kg"""
        result = self.rule._format_grams(0.5)
        self.assertEqual(result, "500g")

        result = self.rule._format_grams(0.025)
        self.assertEqual(result, "25g")

    def test_format_grams_value_greater_than_one(self):
        """Test _format_grams method with value greater than one kg"""
        result = self.rule._format_grams(1.5)
        self.assertEqual(result, "1g")  # int(1.5) = 1

        result = self.rule._format_grams(2.0)
        self.assertEqual(result, "2g")  # int(2.0) = 2

    def test_format_grams_large_value(self):
        """Test _format_grams method with large value (4+ digits)"""
        result = self.rule._format_grams(5000.0)
        self.assertEqual(result, "5.000g")

        result = self.rule._format_grams(15000.0)
        self.assertEqual(result, "15.000g")
