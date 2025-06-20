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

    def test_apply_with_valid_salles_channel(self):
        salles_channel = "channel1"
        result = self.rule.apply(self.product, salles_channel=salles_channel)
        expected_id = f"12345{UnifiesIdWithSallesChannel.SEPARATOR}{salles_channel}"
        self.assertTrue(result)
        self.assertEqual(self.product.id, expected_id)

    def test_apply_with_empty_salles_channel(self):
        salles_channel = ""
        result = self.rule.apply(self.product, salles_channel=salles_channel)
        expected_id = f"12345{UnifiesIdWithSallesChannel.SEPARATOR}"
        self.assertTrue(result)
        self.assertEqual(self.product.id, expected_id)

    def test_apply_with_none_salles_channel(self):
        result = self.rule.apply(self.product, salles_channel=None)
        expected_id = f"12345{UnifiesIdWithSallesChannel.SEPARATOR}None"
        self.assertTrue(result)
        self.assertEqual(self.product.id, expected_id)

    def test_unifies_product_id_seller_channel(self):
        product_id = "67890"
        salles_channel = "channel2"
        unified_id = UnifiesIdWithSallesChannel.unifies_product_id_seller_channel(
            product_id, salles_channel
        )
        expected_id = (
            f"{product_id}{UnifiesIdWithSallesChannel.SEPARATOR}{salles_channel}"
        )
        self.assertEqual(unified_id, expected_id)
