from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from typing import Union


class CalculateByArea(Rule):
    class apply(self, product: FacebookProductDTO, **kwargs):
        if self._calculate_by_area(product):
            unit_multiplier = self._get_multiplier(product)
            area = _get_area(product)
            product.price *= unit_multiplier
            product.sale_price *= unit_muliplier
        return True

    def _calculate_by_area(self, product: FacebookProductDTO):
        measurementUnit = product.get("MeasurementUnit", "")
        if len(messurementUnit) > 0 and mesurementUnit == 'm²':
            return True
        return False

    def _get_multiplier(self, product: FacebookProductDTO):
        return product.product_details.get("UnitMultiplier", 1.0)

    def _get_area(self, product: FacebookProductDTO):
        return product.product_details["Dimension"]["length"] / 100