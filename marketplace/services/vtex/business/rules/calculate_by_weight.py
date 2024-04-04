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
                formatted_price = float(f"{product.sale_price / 100:.2f}")
                price_per_kg = formatted_price / unit_multiplier

            product.description = (
                f"{product.title} - Aprox. {self._format_grams(weight)}, "
                f"Preço do KG: R$ {self._format_price(price_per_kg)}"
            )
            product.title = f"{product.title} Unidade"

        return True

    def _get_multiplier(self, product: FacebookProductDTO) -> float:
        return product.product_details.get("UnitMultiplier", 1.0)

    def _get_weight(self, product: FacebookProductDTO) -> float:
        return product.product_details["Dimension"]["weight"]

    def _calculates_by_weight(self, product: FacebookProductDTO) -> bool:
        title_endings = ["kg", "g", "ml"]
        description_endings = ["kg", "g", "unid", "unidade", "ml"]

        title_lower = product.title.lower()
        description_lower = product.description.lower()

        if any(title_lower.endswith(ending) for ending in title_endings) or any(
            description_lower.endswith(ending) for ending in description_endings
        ):
            return False

        if "iogurte" in (
            category.lower()
            for category in product.product_details["ProductCategories"].values()
        ):
            return False

        categories_to_calculate = [
            "hortifruti",
            "carnes e aves",
            "frios e laticínios",
            "padaria",
        ]
        product_categories = {
            k: v.lower()
            for k, v in product.product_details["ProductCategories"].items()
        }

        for category in categories_to_calculate:
            if category in product_categories.values():
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
