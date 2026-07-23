from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CalculateByArea(Rule):
    """Convert area-based prices (m²) to the price per packaged unit.

    VTEX returns ``listPrice`` per square meter, while the cart simulation
    already applies the ``UnitMultiplier`` to ``sellingPrice`` (the real
    checkout price per box). Only ``price`` must be multiplied here;
    multiplying ``sale_price`` again would apply the multiplier twice.
    """

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        if self._calculate_by_area(product):
            product.price *= self._get_multiplier(product)
        return True

    def _calculate_by_area(self, product: FacebookProductDTO) -> bool:
        return product.product_details.get("MeasurementUnit", "") == "m²"

    def _get_multiplier(self, product: FacebookProductDTO) -> float:
        return product.product_details.get("UnitMultiplier", 1.0)
