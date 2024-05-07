import math
from typing import Tuple

from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class RoundUpCalculateByWeight(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        if self._calculates_by_weight(product):
            unit_multiplier, weight = self._get_product_measurements(product)

            product.price *= unit_multiplier
            product.sale_price *= unit_multiplier

            # Price rounding up
            product.price = math.ceil(product.price)
            product.sale_price = math.ceil(product.sale_price)

            price_per_kg = 0
            if weight > 0:
                formatted_price = float(f"{product.sale_price / 100:.2f}")
                price_per_kg = (formatted_price / unit_multiplier) * 100

            price_per_kg = math.ceil(price_per_kg)
            formatted_price_per_kg = f"{price_per_kg / 100:.2f}"

            product.description = (
                f"{product.title} - Aprox. {self._format_grams(weight)}, "
                f"Preço do KG: R$ {formatted_price_per_kg}"
            )
            product.title = f"{product.title} Unidade"

        return True

    def _get_multiplier(self, product: FacebookProductDTO) -> float:
        return product.product_details.get("UnitMultiplier", 1.0)

    def _get_product_measurements(
        self, product: FacebookProductDTO
    ) -> Tuple[float, float]:
        unit_multiplier = self._get_multiplier(product)
        weight = self._get_weight(product) * unit_multiplier
        return unit_multiplier, weight

    def _get_weight(self, product: FacebookProductDTO) -> float:
        return product.product_details["Dimension"]["weight"]

    def _calculates_by_weight(self, product: FacebookProductDTO) -> bool:
        """
        Determines if the weight calculation should be applied to a product based
        on its categories and description.

        The method checks if the product title or description ends with a unit
        indicator such as 'kg', 'g', or 'ml', which suggests that the product
        is sold by unit and not by weight. If any such indicators are found, the
        product is excluded from weight-based pricing calculations.

        Additionally, the product is excluded if 'iogurte' is among its categories,
        as these are typically sold by volume.

        Finally, the method checks if the product's categories intersect with a
        predefined set of categories known to require weight-based calculations
        ('hortifruti', 'carnes e aves', 'frios e laticínios', 'padaria'). If there
        is no intersection, the product does not qualify for weight-based calculations.

        Returns:
            bool: True if the product should be calculated by weight, False otherwise.
        """
        title_lower = product.title.lower()
        description_lower = product.description.lower()

        if any(title_lower.endswith(ending) for ending in ["kg", "g", "ml"]):
            return False
        if any(
            description_lower.endswith(ending)
            for ending in ["kg", "g", "unid", "unidade", "ml"]
        ):
            return False

        product_categories = {
            value.lower()
            for value in product.product_details["ProductCategories"].values()
        }
        categories_to_calculate = {
            "hortifruti",
            "carnes e aves",
            "frios e laticínios",
            "padaria",
        }

        if "iogurte" in product_categories:
            return False

        return not categories_to_calculate.isdisjoint(product_categories)

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
