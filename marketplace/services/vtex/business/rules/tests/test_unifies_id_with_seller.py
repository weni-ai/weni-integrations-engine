from django.test import TestCase

from marketplace.services.vtex.business.rules.unifies_id_with_seller import (
    UnifiesIdWithSeller,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestUnifiesIdWithSeller(TestCase):
    def setUp(self):
        self.rule = UnifiesIdWithSeller()

    def test_apply_with_seller_id(self):
        product = FacebookProductDTO(
            id="12345",
            title="Produto com ID unificado",
            description="Produto para testar unificação de ID",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={},
        )

        seller_id = "seller789"
        self.rule.apply(product, seller_id=seller_id)
        self.assertEqual(product.id, "12345#seller789")

    def test_create_unique_product_id(self):
        result = UnifiesIdWithSeller.create_unique_product_id("sku123", "seller456")
        self.assertEqual(result, "sku123#seller456")
