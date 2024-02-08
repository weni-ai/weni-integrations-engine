from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from typing import Union


class CalculateByWeight(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        if self._calculates_by_weight(product):
            unit_multiplier = self._get_multiplier(product)
            weight = self._get_weight(product) * unit_multiplier

            product.price *= unit_multiplier
            product.sale_price *= unit_multiplier

            price_per_kg = 0
            if weight > 0:
                formated_price = float(f"{product.price / 100:.2f}")
                price_per_kg = formated_price / unit_multiplier

            product.description = (
                f"{product.title} - Aprox. {self._format_grams(weight)}, "
                f"Preço do KG: R$ {self._format_price(price_per_kg)}"
            )

        return True

    def _get_multiplier(self, product: FacebookProductDTO) -> float:
        return product.product_details.get("UnitMultiplier", 1.0)

    def _get_weight(self, product: FacebookProductDTO) -> float:
        return product.product_details["Dimension"]["weight"]

    def _calculates_by_weight(self, product: FacebookProductDTO) -> bool:
        categories_to_calculate = [
            "hortifruti",
            "carnes e aves",
            "frios e laticínios",
            "padaria",
        ]
        products_categories = {
            k: v.lower()
            for k, v in product.product_details["ProductCategories"].items()
        }

        for category in categories_to_calculate:
            if category in products_categories.values():
                return True

        return False

    def _format_price(self, price: Union[int, float]) -> str:
        return f"{price:.2f}"

    def _format_grams(self, value: float) -> str:
        if 0 < value < 1:
            grams = int(value * 1000)
        else:
            grams = int(value)

        if grams > 999:
            formatted = f"{grams:,}".replace(",", ".")
        else:
            formatted = str(grams)

        return f"{formatted}g"
