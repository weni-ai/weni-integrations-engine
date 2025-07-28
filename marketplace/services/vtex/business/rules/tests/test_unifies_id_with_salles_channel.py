import unittest
from marketplace.services.vtex.business.rules.unifies_id_with_salles_channel import (
    UnifiesIdWithSallesChannel,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestUnifiesIdWithSallesChannel(unittest.TestCase):
    def setUp(self):
        self.rule = UnifiesIdWithSallesChannel()
        self.product = FacebookProductDTO(
            id="12345",
            title="Product with unified id",
            description="Product to test unified id",
            availability="in stock",
            status="active",
            condition="new",
            price="1000",
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price="1000",
            product_details={},
        )

    def test_apply_with_valid_sales_channel(self):
        sales_channel = "channel1"
        result = self.rule.apply(self.product, sales_channel=sales_channel)
        expected_id = f"12345{UnifiesIdWithSallesChannel.SEPARATOR}{sales_channel}"
        self.assertTrue(result)
        self.assertEqual(self.product.id, expected_id)

    def test_apply_with_empty_sales_channel(self):
        sales_channel = ""
        original_id = self.product.id
        result = self.rule.apply(self.product, sales_channel=sales_channel)
        self.assertFalse(result)
        self.assertEqual(self.product.id, original_id)

    def test_apply_with_none_sales_channel(self):
        original_id = self.product.id
        result = self.rule.apply(self.product, sales_channel=None)
        self.assertFalse(result)
        self.assertEqual(self.product.id, original_id)

    def test_unifies_product_id_seller_channel(self):
        product_id = "67890"
        sales_channel = "channel2"
        unified_id = UnifiesIdWithSallesChannel.unifies_product_id_seller_channel(
            product_id, sales_channel
        )
        expected_id = (
            f"{product_id}{UnifiesIdWithSallesChannel.SEPARATOR}{sales_channel}"
        )
        self.assertEqual(unified_id, expected_id)
