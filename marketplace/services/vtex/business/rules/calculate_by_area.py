from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from typing import Union


class CalculateByArea(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        if self._calculate_by_area(product):
            unit_multiplier = self._get_multiplier(product)
            product.price *= unit_multiplier
            product.sale_price *= unit_multiplier
        return True

    def _calculate_by_area(self, product: FacebookProductDTO):
        measurementUnit = product.product_details.get("MeasurementUnit", "")
        if len(measurementUnit) > 0 and measurementUnit == 'm²':
            return True
        return False

    def _get_multiplier(self, product: FacebookProductDTO):
        return product.product_details.get("UnitMultiplier", 1.0)
