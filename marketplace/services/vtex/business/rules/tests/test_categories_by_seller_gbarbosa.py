from unittest.mock import MagicMock
from django.test import TestCase
from marketplace.services.vtex.business.rules.categories_by_seller_gbarbosa import (
    CategoriesBySeller,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestCategoriesBySeller(TestCase):
    def setUp(self):
        self.rule = CategoriesBySeller()

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
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"main": "eletro"},
                "ProductDescription": "Descrição do produto",
                "SkuName": "Nome do SKU",
                "ProductId": "PROD123",
                "Id": "PROD123",
                # Mock for product specifications
                "ProductSpecifications": [
                    {"Name": "Cor", "Value": ["Azul", "Vermelho"]},
                    {"Name": "Tamanho", "Value": ["M", "G"]},
                    {"Name": "Material", "Value": ["Aço inox"]},
                ],
                # Mock for cart simulation data (PIX)
                "CartSimulationData": {
                    "is_available": True,
                    "data": {
                        "paymentData": {
                            "installmentOptions": [
                                {
                                    "paymentName": "pix",
                                    "installments": [
                                        {"value": 70000}
                                    ],  # R$700.00 in cents
                                }
                            ]
                        }
                    },
                },
            },
        )

        # Create a mock service that returns the mocked data
        mock_service = MagicMock()
        mock_service.get_product_specification.return_value = (
            product.product_details.get("ProductSpecifications")
        )
        mock_service.simulate_cart_for_seller.return_value = (
            product.product_details.get("CartSimulationData")
        )

        result = self.rule.apply(
            product, seller_id="gbarbosab101", service=mock_service, domain="test.com"
        )

        self.assertTrue(result)

        # Verify that the product was modified correctly
        self.assertIn("*Características:*", product.description)
        self.assertIn("*Cor* : Azul, Vermelho", product.description)
        self.assertIn("*Tamanho* : M, G", product.description)
        self.assertIn("*Material* : Aço inox", product.description)

        # Verify that the PIX price was applied
        self.assertEqual(product.sale_price, 70000)  # PIX price is lower
        self.assertIn("Preço promocional PIX R$ 700,00", product.description)

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

    def test_get_categories_empty(self):
        """Test _get_categories method with empty categories"""
        product = FacebookProductDTO(
            id="test_empty_categories",
            title="Produto",
            description="Produto sem categorias",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        categories = self.rule._get_categories(product)
        self.assertEqual(categories, set())

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

    def test_product_specification_called(self):
        """Test that product specification is called correctly"""
        product = FacebookProductDTO(
            id="test_specification",
            title="TV",
            description="TV LED 55 pol",
            availability="in stock",
            status="active",
            condition="new",
            price=200000,
            sale_price=180000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "ProductCategories": {"main": "eletrodoméstico"},
                "ProductDescription": "Descrição da TV",
                "SkuName": "TV LED",
                "ProductId": "TV123",
                # Mock for product specifications
                "ProductSpecifications": [
                    {"Name": "Resolução", "Value": ["4K", "HD"]},
                    {"Name": "Tamanho", "Value": ["55 polegadas"]},
                    {"Name": "Tecnologia", "Value": ["LED", "Smart TV"]},
                ],
            },
        )

        # Create a mock service that returns specifications
        mock_service = MagicMock()
        mock_service.get_product_specification.return_value = (
            product.product_details.get("ProductSpecifications")
        )

        # Call the method directly to test
        result = self.rule._product_specification(product, mock_service, "test.com")

        # Verify that the method works correctly
        self.assertIn("*Características:*", result)
        self.assertIn("*Resolução* : 4K, HD", result)
        self.assertIn("*Tamanho* : 55 polegadas", result)
        self.assertIn("*Tecnologia* : LED, Smart TV", result)

        # Verify that the service was called correctly
        mock_service.get_product_specification.assert_called_once_with(
            "TV123", "test.com"
        )

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

    def test_extract_pix_value_with_pix(self):
        """Test _extract_pix_value method with PIX payment"""
        availability_details = {
            "data": {
                "paymentData": {
                    "installmentOptions": [
                        {"paymentName": "pix", "installments": [{"value": 45000}]}
                    ]
                }
            }
        }

        result = self.rule._extract_pix_value(availability_details)
        self.assertEqual(result, 45000)

    def test_extract_pix_value_no_pix(self):
        """Test _extract_pix_value method without PIX payment"""
        availability_details = {
            "data": {
                "paymentData": {
                    "installmentOptions": [
                        {
                            "paymentName": "credit_card",
                            "installments": [{"value": 50000}],
                        }
                    ]
                }
            }
        }

        result = self.rule._extract_pix_value(availability_details)
        self.assertEqual(result, None)

    def _extract_pix_value_empty_installments(self):
        """Test _extract_pix_value method with empty installments"""
        availability_details = {
            "data": {
                "paymentData": {
                    "installmentOptions": [{"paymentName": "pix", "installments": []}]
                }
            }
        }

        result = self.rule._extract_pix_value(availability_details)
        self.assertEqual(result, None)

    def test_extract_pix_value_missing_data(self):
        """Test _extract_pix_value method with missing data structure"""
        availability_details = {}

        result = self.rule._extract_pix_value(availability_details)
        self.assertEqual(result, None)

    def test_append_pix_promotion_description(self):
        """Test _append_pix_promotion_description method"""
        product = FacebookProductDTO(
            id="test_pix_desc",
            title="Produto PIX",
            description="Descrição original",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={},
        )

        self.rule._append_pix_promotion_description(product, 40000, 45000)

        self.assertIn("Preço promocional PIX R$ 400,00", product.description)
        self.assertIn("R$ 450,00 em outras modalidades", product.description)
        self.assertEqual(product.rich_text_description, product.description)

    def test_format_price(self):
        """Test _format_price method"""
        result = self.rule._format_price(45000)
        self.assertEqual(result, "450,00")

        result = self.rule._format_price(1234)
        self.assertEqual(result, "12,34")

        result = self.rule._format_price(1000000)
        self.assertEqual(result, "10.000,00")

    def test_fetch_and_update_pix_price_no_availability(self):
        """Test _fetch_and_update_pix_price method when product not available"""
        product = FacebookProductDTO(
            id="test_no_availability",
            title="Produto Indisponível",
            description="Produto temporariamente fora de estoque",
            availability="out of stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "Id": "PROD123",
                "CartSimulationData": {"is_available": False},
            },
        )

        mock_service = MagicMock()
        mock_service.simulate_cart_for_seller.return_value = (
            product.product_details.get("CartSimulationData")
        )

        self.rule._fetch_and_update_pix_price(
            product, mock_service, "gbarbosab101", "test.com"
        )

        self.assertEqual(product.sale_price, 45000)

    def test_fetch_and_update_pix_price_no_sale_price(self):
        """Test _fetch_and_update_pix_price method when product has no sale_price"""
        product = FacebookProductDTO(
            id="test_no_sale_price",
            title="Produto sem Preço de Venda",
            description="Produto apenas com preço normal",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=None,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "Id": "PROD123",
                "CartSimulationData": {"is_available": True},
            },
        )

        mock_service = MagicMock()
        mock_service.simulate_cart_for_seller.return_value = (
            product.product_details.get("CartSimulationData")
        )

        self.rule._fetch_and_update_pix_price(
            product, mock_service, "gbarbosab101", "test.com"
        )

        self.assertEqual(product.sale_price, 50000)  # Set to price value

    def test_fetch_and_update_pix_price_higher_pix_price(self):
        """Test _fetch_and_update_pix_price method when PIX price is higher than current"""
        product = FacebookProductDTO(
            id="test_higher_pix",
            title="Produto PIX Alto",
            description="Produto com PIX mais alto",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="TestBrand",
            product_details={
                "Id": "PROD123",
                "CartSimulationData": {
                    "is_available": True,
                    "data": {
                        "paymentData": {
                            "installmentOptions": [
                                {
                                    "paymentName": "pix",
                                    "installments": [{"value": 48000}],
                                }
                            ]
                        }
                    },
                },
            },
        )

        mock_service = MagicMock()
        mock_service.simulate_cart_for_seller.return_value = (
            product.product_details.get("CartSimulationData")
        )

        self.rule._fetch_and_update_pix_price(
            product, mock_service, "gbarbosab101", "test.com"
        )

        self.assertEqual(product.sale_price, 45000)  # PIX is higher
        self.assertNotIn("Preço promocional PIX", product.description)
