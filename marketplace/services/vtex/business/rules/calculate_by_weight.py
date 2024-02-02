from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CalculateByWeight(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        if self._calculates_by_weight(product):
            unit_multiplier = self._get_multiplier(product)
            weight = self._get_weight(product) * unit_multiplier
            price_per_kg = product.price * unit_multiplier
            product.price *= unit_multiplier
            product.sale_price *= unit_multiplier
            product.description = (
                f"{product.title} - Aprox. {weight}g, Preço do KG: {price_per_kg}"
            )

        return True

    def _get_multiplier(self, product: FacebookProductDTO) -> float:
        return product.product_details.get("UnitMultiplier", 1.0)

    def _get_weight(self, product: FacebookProductDTO) -> float:
        return product.product_details["Dimension"]["weight"]

    def _calculates_by_weight(self, product: FacebookProductDTO) -> bool:
        categories_to_calculate = [
            "Hortifruti",
            "Carnes e Aves",
            "Frios e Laticínios",
            "Padaria",
        ]
        products_categories = product.product_details["ProductCategories"]

        for category in categories_to_calculate:
            if category in products_categories.values():
                return True
        return False