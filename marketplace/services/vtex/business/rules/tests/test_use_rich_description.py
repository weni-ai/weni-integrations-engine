from django.test import TestCase
from marketplace.services.vtex.business.rules.use_rich_description import (
    UseRichDescription,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestUseRichDescription(TestCase):
    def setUp(self):
        self.rule = UseRichDescription()

    def test_apply_with_product_description(self):
        """Test apply method when ProductDescription exists"""
        product = FacebookProductDTO(
            id="test_rich_desc_1",
            title="Produto com Descrição Rica",
            description="Descrição simples do produto",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "Descrição detalhada e rica do produto com especificações técnicas",
                "SkuName": "SKU123",
            },
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description,
            "Descrição detalhada e rica do produto com especificações técnicas",
        )

    def test_apply_with_empty_product_description(self):
        """Test apply method when ProductDescription is empty"""
        product = FacebookProductDTO(
            id="test_rich_desc_2",
            title="Produto sem Descrição Rica",
            description="Descrição simples do produto",
            availability="in stock",
            status="active",
            condition="new",
            price=25000,
            sale_price=22000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "",
                "SkuName": "Nome detalhado do SKU do produto",
            },
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description, "Nome detalhado do SKU do produto"
        )

    def test_apply_with_none_product_description(self):
        """Test apply method when ProductDescription is None"""
        product = FacebookProductDTO(
            id="test_rich_desc_3",
            title="Produto com Descrição Null",
            description="Descrição simples do produto",
            availability="in stock",
            status="active",
            condition="new",
            price=15000,
            sale_price=13000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": None,
                "SkuName": "SKU sem descrição completa",
            },
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description, None
        )  # Current behavior returns None for None ProductDescription

    def test_apply_short_product_description(self):
        """Test apply method with short ProductDescription"""
        product = FacebookProductDTO(
            id="test_rich_desc_4",
            title="Produto Descrição Curta",
            description="Descrição simples",
            availability="in stock",
            status="active",
            condition="new",
            price=8000,
            sale_price=7500,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "Curta",
                "SkuName": "SKU Longo e Detalhado",
            },
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(product.rich_text_description, "Curta")

    def test_get_description_with_valid_description(self):
        """Test _get_description method with valid ProductDescription"""
        product = FacebookProductDTO(
            id="test_desc_valid",
            title="Produto Teste",
            description="Descrição teste",
            availability="in stock",
            status="active",
            condition="new",
            price=10000,
            sale_price=9000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "Descrição válida do produto",
                "SkuName": "SKU123",
            },
        )

        description = self.rule._get_description(product)

        self.assertEqual(description, "Descrição válida do produto")

    def test_get_description_empty_string(self):
        """Test _get_description method with empty string ProductDescription"""
        product = FacebookProductDTO(
            id="test_desc_empty",
            title="Produto Teste Vazio",
            description="Descrição teste",
            availability="in stock",
            status="active",
            condition="new",
            price=5000,
            sale_price=4500,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "",
                "SkuName": "SKU com descrição alternativa",
            },
        )

        description = self.rule._get_description(product)

        self.assertEqual(description, "SKU com descrição alternativa")

    def test_get_description_whitespace_string(self):
        """Test _get_description method with whitespace-only ProductDescription"""
        product = FacebookProductDTO(
            id="test_desc_whitespace",
            title="Produto Teste Espaços",
            description="Descrição teste",
            availability="in stock",
            status="active",
            condition="new",
            price=12000,
            sale_price=11000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "   ",  # Whitespace only
                "SkuName": "SKU com nome importante",
            },
        )

        description = self.rule._get_description(product)

        self.assertEqual(description, "   ")  # Whitespace string ≠ empty string

    def test_get_description_none_value(self):
        """Test _get_description method with None ProductDescription"""
        product = FacebookProductDTO(
            id="test_desc_none",
            title="Produto Teste None",
            description="Descrição teste",
            availability="in stock",
            status="active",
            condition="new",
            price=7500,
            sale_price=6800,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": None,
                "SkuName": "SKU padrão quando descrição é None",
            },
        )

        description = self.rule._get_description(product)

        self.assertEqual(
            description, None
        )  # Current behavior returns None for None ProductDescription

    def test_apply_with_kwargs(self):
        """Test apply method with additional kwargs (should be ignored)"""
        product = FacebookProductDTO(
            id="test_kwargs",
            title="Produto com Kwargs",
            description="Descrição básica",
            availability="in stock",
            status="active",
            condition="new",
            price=20000,
            sale_price=18000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details={
                "ProductDescription": "Descrição final do produto",
                "SkuName": "SKU432",
            },
        )

        result = self.rule.apply(
            product, seller_id="test", service=None, domain="example.com"
        )

        self.assertTrue(result)
        self.assertEqual(product.rich_text_description, "Descrição final do produto")
