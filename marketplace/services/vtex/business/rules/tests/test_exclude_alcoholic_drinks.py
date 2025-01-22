from django.test import TestCase
from marketplace.services.vtex.business.rules.exclude_alcoholic_drinks import (
    ExcludeAlcoholicDrinks,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestExcludeAlcoholicDrinks(TestCase):
    def setUp(self):
        self.rule = ExcludeAlcoholicDrinks()

    def test_apply_excludes_alcohol(self):
        product = FacebookProductDTO(
            id="test_alcohol",
            title="Wine Bottle",
            description="Red wine",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=900,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="Brand Name",
            product_details={"ProductCategories": {"1": "vinos y licores"}},
        )

        result = self.rule.apply(product)
        self.assertFalse(result)

    def test_apply_non_alcoholic(self):
        product = FacebookProductDTO(
            id="test_non_alcoholic",
            title="Batata Doce",
            description="Produto sem álcool",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            sale_price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="Brand Name",
            product_details={"ProductCategories": {"1": "frutas"}},
        )

        result = self.rule.apply(product)
        self.assertTrue(result)
