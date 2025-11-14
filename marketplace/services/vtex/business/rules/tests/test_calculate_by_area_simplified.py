from django.test import TestCase
from marketplace.services.vtex.business.rules.calculate_by_area import CalculateByArea
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCalculateByArea(TestCase):
    def setUp(self):
        self.rule = CalculateByArea()

    def create_product(self, measurement_unit=None, multiplier=None):
        """Helper method to create test products"""

        product_details = {
            "MeasurementUnit": measurement_unit or "",
            "UnitMultiplier": multiplier or 1.0,
        }

        return FacebookProductDTO(
            id="test_product",
            title="Produto Teste",
            description="Produto de teste",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,  # R$100.00 in cents
            sale_price=8000,  # R$80.00 in cents
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details=product_details,
        )

    def test_apply_with_area_calculation(self):
        """Test apply method when product should be calculated by area"""
        product = self.create_product(measurement_unit="m²", multiplier=2.5)

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 25000)  # 10000 * 2.5
        self.assertEqual(product.sale_price, 20000)  # 8000 * 2.5

    def test_apply_without_area_calculation(self):
        """Test apply method when product should not be calculated by area"""
        product = self.create_product(measurement_unit="un")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_empty_measurement_unit(self):
        """Test apply method with empty measurement unit"""
        product = self.create_product(measurement_unit="")

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_missing_measurement_unit(self):
        """Test apply method when measurement unit is missing"""
        product = self.create_product(measurement_unit=None)

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_default_multiplier(self):
        """Test apply method with default multiplier"""
        product = self.create_product()

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)  # 10000 * 1.0 (no area calculation)
        self.assertEqual(product.sale_price, 8000)  # 8000 * 1.0 (no area calculation)

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

    def test_calculate_by_area_true(self):
        """Test _calculate_by_area method returns True for m²"""
        product = self.create_product(measurement_unit="m²")

        result = self.rule._calculate_by_area(product)

        self.assertTrue(result)

    def test_calculate_by_area_false_un(self):
        """Test _calculate_by_area method returns False for un"""
        product = self.create_product(measurement_unit="un")

        result = self.rule._calculate_by_area(product)

        self.assertFalse(result)

    def test_calculate_by_area_false_empty(self):
        """Test _calculate_by_area method returns False for empty unit"""
        product = self.create_product(measurement_unit="")

        result = self.rule._calculate_by_area(product)

        self.assertFalse(result)
