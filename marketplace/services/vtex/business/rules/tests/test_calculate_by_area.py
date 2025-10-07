from django.test import TestCase
from marketplace.services.vtex.business.rules.calculate_by_area import CalculateByArea
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCalculateByArea(TestCase):
    def setUp(self):
        self.rule = CalculateByArea()

    def test_apply_with_area_calculation(self):
        """Test apply method when product should be calculated by area"""
        product = FacebookProductDTO(
            id="test_area_1",
            title="Produto por Área",
            description="Produto vendido por metro quadrado",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,  # R$100.00 in cents
            sale_price=8000,  # R$80.00 in cents
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"MeasurementUnit": "m²", "UnitMultiplier": 2.5},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 25000)  # 10000 * 2.5
        self.assertEqual(product.sale_price, 20000)  # 8000 * 2.5

    def test_apply_without_area_calculation(self):
        """Test apply method when product should not be calculated by area"""
        product = FacebookProductDTO(
            id="test_normal",
            title="Produto Normal",
            description="Produto vendido por unidade",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "MeasurementUnit": "un",  # unidad, not area
                "UnitMultiplier": 2.5,
            },
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_empty_measurement_unit(self):
        """Test apply method with empty measurement unit"""
        product = FacebookProductDTO(
            id="test_empty",
            title="Produto sem Unidade",
            description="Produto sem unidade de medida",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"MeasurementUnit": "", "UnitMultiplier": 2.5},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_missing_measurement_unit(self):
        """Test apply method when measurement unit is missing"""
        product = FacebookProductDTO(
            id="test_missing",
            title="Produto sem Medida",
            description="Produto sem configuração de medida",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)
        self.assertEqual(product.sale_price, 8000)

    def test_apply_zero_multiplier(self):
        """Test apply method with zero multiplier"""
        product = FacebookProductDTO(
            id="test_zero",
            title="Produto Multiplicador Zero",
            description="Produto com multiplicador zero",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 10000)  # because zero multiplier doesn't apply
        self.assertEqual(
            product.sale_price, 8000
        )  # because zero multiplier doesn't apply

    def test_apply_default_multiplier(self):
        """Test apply method with default multiplier"""
        product = FacebookProductDTO(
            id="test_default",
            title="Produto Padrão",
            description="Produto com multiplicador padrão",
            availability="in stock",
            status="active",
            condition="new",
            price=15000,
            sale_price=12000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.price, 15000)  # 15000 * 1.0
        self.assertEqual(product.sale_price, 12000)  # 12000 * 1.0

    def test_get_multiplier_with_value(self):
        """Test _get_multiplier method with valid value"""
        product = FacebookProductDTO(
            id="test_multiplier",
            title="Produto Multiplicador",
            description="Teste do multiplicador",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"UnitMultiplier": 3.5},
        )

        multiplier = self.rule._get_multiplier(product)

        self.assertEqual(multiplier, 3.5)

    def test_get_multiplier_default(self):
        """Test _get_multiplier method with default value"""
        product = FacebookProductDTO(
            id="test_default_multiplier",
            title="Produto Multiplicador Padrão",
            description="Teste do multiplicador padrão",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        multiplier = self.rule._get_multiplier(product)

        self.assertEqual(multiplier, 1.0)

    def test_calculate_by_area_true(self):
        """Test _calculate_by_area method returns True for m²"""
        product = FacebookProductDTO(
            id="test_area_true",
            title="Produto Área Verdadeiro",
            description="Produto com unidade m²",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"MeasurementUnit": "m²"},
        )

        result = self.rule._calculate_by_area(product)

        self.assertTrue(result)

    def test_calculate_by_area_false_un(self):
        """Test _calculate_by_area method returns False for un"""
        product = FacebookProductDTO(
            id="test_area_false",
            title="Produto Área Falso",
            description="Produto com unidade un",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"MeasurementUnit": "un"},
        )

        result = self.rule._calculate_by_area(product)

        self.assertFalse(result)

    def test_calculate_by_area_false_empty(self):
        """Test _calculate_by_area method returns False for empty unit"""
        product = FacebookProductDTO(
            id="test_area_empty",
            title="Produto Área Vazio",
            description="Produto sem unidade",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=8000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"MeasurementUnit": ""},
        )

        result = self.rule._calculate_by_area(product)

        self.assertFalse(result)
