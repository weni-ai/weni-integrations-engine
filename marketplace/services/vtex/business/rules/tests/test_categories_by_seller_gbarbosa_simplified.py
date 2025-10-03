from django.test import TestCase
from marketplace.services.vtex.business.rules.categories_by_seller_gbarbosa import (
    CategoriesBySeller,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class MockVTEXService:
    """Mock service to simulate VTEX API calls without complex patches"""

    def __init__(self):
        self.call_count = 0
        self.product_id = None
        self.seller_id = None
        self.domain = None

    def get_product_specification(self, product_id, domain):
        """Mock product specification call"""
        self.call_count += 1
        self.product_id = product_id
        self.domain = domain

        return [
            {"Name": "Cor", "Value": ["Azul", "Vermelho"]},
            {"Name": "Tamanho", "Value": ["M", "G"]},
            {"Name": "Material", "Value": ["Algodão"]},
        ]

    def simulate_cart_for_seller(self, product_id, seller_id, domain):
        """Mock cart simulation call"""
        self.call_count += 1
        self.product_id = product_id
        self.seller_id = seller_id
        self.domain = domain

        # Simulate available product with PIX discount
        return {
            "is_available": True,
            "data": {
                "paymentData": {
                    "installmentOptions": [
                        {
                            "paymentName": "pix",
                            "installments": [{"value": 40000}],  # R$400.00 in cents
                        }
                    ]
                }
            },
        }


class TestCategoriesBySeller(TestCase):
    def setUp(self):
        self.rule = CategoriesBySeller()
        self.mock_service = MockVTEXService()

    def test_apply_non_home_appliance_product(self):
        """Test apply method with non-home appliance product"""
        product = FacebookProductDTO(
            id="test_no_appliance",
            title="Produto Normal",
            description="Produto comum",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"ProductCategories": {"main": "perfumaria"}},
        )

        result = self.rule.apply(product, seller_id="gbarbosab101")

        self.assertTrue(result)
        self.assertEqual(product.description, "Produto comum")

    def test_apply_home_appliance_wrong_seller(self):
        """Test apply method with home appliance but wrong seller"""
        product = FacebookProductDTO(
            id="test_wrong_seller",
            title="Microondas",
            description="Microondas modelo X",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"main": "eletrodoméstico"},
                "ProductDescription": "Descrição do produto",
                "SkuName": "Nome do SKU",
            },
        )

        result = self.rule.apply(product, seller_id="other_seller")

        self.assertFalse(result)
        self.assertEqual(product.description, "Microondas modelo X")

    def test_apply_home_appliance_correct_seller(self):
        """Test apply method with home appliance and correct seller"""
        product = FacebookProductDTO(
            id="test_appliance",
            title="Geladeira",
            description="Geladeira modelo Y",
            availability="in stock",
            status="active",
            condition="new",
            price=80000,
            sale_price=75000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"main": "eletro"},
                "ProductDescription": "Descrição do produto",
                "SkuName": "Nome do SKU",
                "ProductId": "PROD123",
            },
        )

        result = self.rule.apply(
            product,
            seller_id="gbarbosab101",
            service=self.mock_service,
            domain="test.com",
        )

        self.assertTrue(result)
        self.assertIn("Características:", product.description)
        self.assertIn("*Cor* : Azul, Vermelho", product.description)
        self.assertIn("*Tamanho* : M, G", product.description)
        self.assertIn("*Material* : Algodão", product.description)

        # Verify service was called correctly
        self.assertGreater(
            self.mock_service.call_count, 0
        )  # Service was called at least once


# Mock service for non-availability tests
class MockVTEXServiceNotAvailable:
    def simulate_cart_for_seller(self, product_id, seller_id, domain):
        return {"is_available": False}

    def get_product_specification(self, product_id, domain):
        return []


class TestCategoriesBySellerAvailability(TestCase):
    def setUp(self):
        self.rule = CategoriesBySeller()
        self.mock_service = MockVTEXServiceNotAvailable()

    def test_apply_home_appliance_not_available(self):
        """Test case when product is not available"""
        product = FacebookProductDTO(
            id="test_unavailable",
            title="TV Indisponível",
            description="TV temporariamente fora",
            availability="out of stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"main": "eletrodoméstico"},
                "ProductDescription": "Descrição do produto",
                "SkuName": "Nome do SKU",
                "ProductId": "PROD123",
                "Id": "PROD123",
            },
        )

        result = self.rule.apply(
            product,
            seller_id="gbarbosab101",
            service=self.mock_service,
            domain="test.com",
        )

        self.assertTrue(result)
        # Should not change sale_price when not available
        self.assertEqual(product.sale_price, 45000)


# Test cases for methods that don't require complex mocking
class TestCategoriesBySellerMethods(TestCase):
    def setUp(self):
        self.rule = CategoriesBySeller()

    def test_get_categories(self):
        """Test _get_categories method"""
        product = FacebookProductDTO(
            id="test_categories",
            title="Produto",
            description="Produto de teste",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {
                    "main": "ELETRODOMÉSTICO",
                    "sub": "eletroportáteis",
                    "other": "ELETRO",
                }
            },
        )

        categories = self.rule._get_categories(product)
        expected = {"eletrodoméstico", "eletroportáteis", "eletro"}
        self.assertEqual(categories, expected)

    def test_is_home_appliance_true(self):
        """Test _is_home_appliance method returning True"""
        product = FacebookProductDTO(
            id="test_appliance_true",
            title="Fogão",
            description="Fogão de 4 bocas",
            availability="in stock",
            status="active",
            condition="new",
            price=30000,
            sale_price=28000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"ProductCategories": {"main": "eletrodoméstico"}},
        )

        result = self.rule._is_home_appliance(product)
        self.assertTrue(result)

    def test_is_home_appliance_false(self):
        """Test _is_home_appliance method returning False"""
        product = FacebookProductDTO(
            id="test_appliance_false",
            title="Perfume",
            description="Perfume importado",
            availability="in stock",
            status="active",
            condition="new",
            price=15000,
            sale_price=12000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={"ProductCategories": {"main": "perfumaria"}},
        )

        result = self.rule._is_home_appliance(product)
        self.assertFalse(result)

    def test_product_description_with_desc(self):
        """Test _product_description method when ProductDescription exists"""
        product = FacebookProductDTO(
            id="test_desc_with_desc",
            title="Produto",
            description="Produto com descrição",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "Descrição detalhada do produto",
                "SkuName": "Nome simples",
            },
        )

        description = self.rule._product_description(product)
        self.assertEqual(description, "Descrição detalhada do produto")

    def test_product_description_without_desc(self):
        """Test _product_description method when ProductDescription is empty"""
        product = FacebookProductDTO(
            id="test_desc_without_desc",
            title="Produto",
            description="Produto sem descrição",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "",
                "SkuName": "Nome do produto extenso e detalhado",
            },
        )

        description = self.rule._product_description(product)
        self.assertEqual(description, "Nome do produto extenso e detalhado")

    def test_truncate_text_no_truncation(self):
        """Test _truncate_text method when text doesn't need truncation"""
        text = "Texto pequeno"
        result = self.rule._truncate_text(text, 100)
        self.assertEqual(result, "Texto pequeno")

    def test_truncate_text_with_truncation(self):
        """Test _truncate_text method when text needs truncation"""
        text = "A" * 200  # 200 characters
        result = self.rule._truncate_text(text, 100)
        self.assertEqual(len(result), 100)
        self.assertEqual(result, "A" * 100)

    def test_format_price(self):
        """Test _format_price method"""
        result = self.rule._format_price(45000)
        self.assertEqual(result, "450,00")

        result = self.rule._format_price(1234)
        self.assertEqual(result, "12,34")

        result = self.rule._format_price(1000000)
        self.assertEqual(result, "10.000,00")
