from django.test import TestCase

from marketplace.services.vtex.business.rules.exclude_categories_co import (
    ExcludeCustomizedCategoriesCO,
)
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class TestExcludeCustomizedCategoriesCO(TestCase):
    def setUp(self):
        self.rule = ExcludeCustomizedCategoriesCO()

    def test_apply_with_excluded_category(self):
        product = FacebookProductDTO(
            id="12345",
            title="Produto em categoria excluída",
            description="Produto que pertence a uma categoria personalizada excluída",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={"ProductCategories": {"1": "Cigarrillos y Tabacos"}},
        )

        result = self.rule.apply(product)
        self.assertFalse(result)

    def test_apply_with_included_category(self):
        product = FacebookProductDTO(
            id="67890",
            title="Produto em categoria permitida",
            description="Produto que pertence a uma categoria não excluída",
            availability="in stock",
            status="active",
            condition="new",
            price=1000,
            link="http://example.com/product",
            image_link="http://example.com/image.jpg",
            brand="ExampleBrand",
            sale_price=1000,
            product_details={"ProductCategories": {"1": "Frutas e Verduras"}},
        )

        result = self.rule.apply(product)
        self.assertTrue(result)
