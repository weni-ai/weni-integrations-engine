from django.test import TestCase
from marketplace.services.vtex.business.rules.set_default_image_url import (
    SetDefaultImageURL,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestSetDefaultImageURL(TestCase):
    def setUp(self):
        self.rule = SetDefaultImageURL()

    def test_set_image_url(self):
        product = FacebookProductDTO(
            id="test_image",
            title="Produto com nova imagem",
            description="Produto para teste de URL da imagem",
            availability="in stock",
            status="active",
            condition="new",
            price=200,
            sale_price=200,
            link="http://example.com/product",
            image_link="http://example.com/old_image.jpg",
            brand="ExampleBrand",
            product_details={"ImageUrl": "http://example.com/new_image.jpg"},
        )

        self.rule.apply(product)

        self.assertEqual(product.image_link, "http://example.com/new_image.jpg")
