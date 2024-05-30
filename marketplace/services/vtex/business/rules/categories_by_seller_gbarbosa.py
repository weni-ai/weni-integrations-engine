from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CategoriesBySeller(Rule):
    HOME_APPLIANCES_CATEGORIES = {"eletrodoméstico", "eletro", "eletroportáteis"}

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        seller_id = kwargs.get("seller_id")
        if self._is_home_appliance(product):
            # Only seller gbarbosab101 can have appliances
            if seller_id != "gbarbosab101":
                return False
        # If the product is not an appliance, it can be added by any seller
        return True

    def _get_categories(self, product: FacebookProductDTO) -> set:
        return set(
            category.lower()
            for category in product.product_details.get(
                "ProductCategories", {}
            ).values()
        )

    def _is_home_appliance(self, product: FacebookProductDTO) -> bool:
        product_categories = self._get_categories(product)
        return bool(self.HOME_APPLIANCES_CATEGORIES.intersection(product_categories))
