from django.test import TestCase
from marketplace.services.vtex.business.rules.use_rich_description import (
    UseRichDescription,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestUseRichDescription(TestCase):
    def setUp(self):
        self.rule = UseRichDescription()

    def create_product(self, product_description=None, sku_name=None):
        """Helper method to create test products"""

        product_details = {
            "ProductDescription": product_description,
            "SkuName": sku_name or "Default SKU",
        }

        return FacebookProductDTO(
            id="test_product",
            title="Produto Teste",
            description="Descrição simples",
            availability="in stock",
            status="active",
            condition="new",
            price=50000,
            sale_price=45000,
            link="http://example.com/product",
            image_link="http://example.com/product.jpg",
            brand="TestBrand",
            product_details=product_details,
        )

    def test_apply_with_product_description(self):
        """Test apply method when ProductDescription exists"""
        product = self.create_product(
            product_description="Descrição detalhada e rica do produto"
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description, "Descrição detalhada e rica do produto"
        )

    def test_apply_with_empty_product_description(self):
        """Test apply method when ProductDescription is empty"""
        product = self.create_product(
            product_description="", sku_name="Nome detalhado do SKU do produto"
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description, "Nome detalhado do SKU do produto"
        )

    def test_apply_with_none_product_description(self):
        """Test apply method when ProductDescription is None"""
        product = self.create_product(
            product_description=None, sku_name="SKU sem descrição completa"
        )

        result = self.rule.apply(product)

        self.assertTrue(result)
        self.assertEqual(
            product.rich_text_description, None
        )  # Current behavior returns None for None ProductDescription

    def test_apply_with_kwargs(self):
        """Test apply method with additional kwargs (should be ignored)"""
        product = self.create_product(
            product_description="Descrição final do produto", sku_name="SKU432"
        )

        result = self.rule.apply(
            product, seller_id="seller123", service=None, domain="example.com"
        )

        self.assertTrue(result)
        self.assertEqual(product.rich_text_description, "Descrição final do produto")

    def test_get_description_with_valid_description(self):
        """Test _get_description method with valid ProductDescription"""
        product = self.create_product(product_description="Descrição válida")

        description = self.rule._get_description(product)

        self.assertEqual(description, "Descrição válida")

    def test_get_description_empty_string(self):
        """Test _get_description method with empty string ProductDescription"""
        product = self.create_product(
            product_description="", sku_name="SKU com descrição alternativa"
        )

        description = self.rule._get_description(product)

        self.assertEqual(description, "SKU com descrição alternativa")

    def test_get_description_whitespace_string(self):
        """Test _get_description method with whitespace-only ProductDescription"""
        product = self.create_product(
            product_description="   ",  # Whitespace only
            sku_name="SKU com nome importante",
        )

        description = self.rule._get_description(product)

        self.assertEqual(description, "   ")  # Whitespace string ≠ empty string

    def test_get_description_none_value(self):
        """Test _get_description method with None ProductDescription"""
        product = self.create_product(
            product_description=None, sku_name="SKU padrão quando descrição é None"
        )

        description = self.rule._get_description(product)

        self.assertEqual(
            description, None
        )  # Current behavior returns None for None ProductDescription
