from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class ExcludeCustomizedCategoriesCO(Rule):
    """
    Rule to exclude specific product categories for Colombia.
    """

    CUSTOMIZED_EXCLUDED_CATEGORIES = {
        "cigarrillos y tabacos",
        "tabacos",
        "cigarrillos",
    }

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        """
        Excludes products based on specified categories.

        Args:
            product (FacebookProductDTO): Product to check.

        Returns:
            bool: True if the product should be included, False if it is excluded.
        """
        if self._is_customized_excluded_category(product):
            return False  # Excluded product
        return True  # Product is valid

    def _is_customized_excluded_category(self, product: FacebookProductDTO) -> bool:
        """
        Checks if the product is in the excluded categories.

        Args:
            product (FacebookProductDTO): Product to check.

        Returns:
            bool: True if the product is in an excluded category.
        """
        product_categories = set(
            category.lower()
            for category in product.product_details.get(
                "ProductCategories", {}
            ).values()
        )
        return bool(
            self.CUSTOMIZED_EXCLUDED_CATEGORIES.intersection(product_categories)
        )
