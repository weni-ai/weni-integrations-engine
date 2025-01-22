from django.test import TestCase

from marketplace.services.vtex.business.rules.use_extra_imgs import UseExtraImgs
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestUseExtraImgs(TestCase):
    def setUp(self):
        self.rule = UseExtraImgs()

    def test_apply_with_multiple_images(self):
        product = FacebookProductDTO(
            id="test1",
            title="Produto com imagens extras",
            description="Produto com várias imagens",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={
                "Images": [
                    {"ImageUrl": "http://example.com/image1.jpg"},
                    {"ImageUrl": "http://example.com/image2.jpg"},
                    {"ImageUrl": "http://example.com/image3.jpg"},
                ]
            },
        )

        self.rule.apply(product)
        self.assertEqual(
            product.additional_image_link,
            "http://example.com/image2.jpg,http://example.com/image3.jpg",
        )

    def test_apply_with_single_image(self):
        product = FacebookProductDTO(
            id="test2",
            title="Produto com uma imagem",
            description="Produto com uma única imagem",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={
                "Images": [
                    {"ImageUrl": "http://example.com/image1.jpg"},
                ]
            },
        )

        self.rule.apply(product)
        self.assertEqual(product.additional_image_link, "")

    def test_apply_exceeds_2000_characters(self):
        # Create longer URLs to exceed the 2000 character limit
        long_url = "http://example.com/" + "a" * 1990
        product = FacebookProductDTO(
            id="test3",
            title="Produto com muitas imagens",
            description="Produto com imagens extras longas",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={
                "Images": [
                    {"ImageUrl": long_url},
                    {"ImageUrl": long_url},
                    {"ImageUrl": "http://example.com/extra_image.jpg"},
                ]
            },
        )

        rule = UseExtraImgs()
        rule.apply(product)

        self.assertTrue(len(product.additional_image_link) <= 2000)
        self.assertNotIn(
            "http://example.com/extra_image.jpg", product.additional_image_link
        )
