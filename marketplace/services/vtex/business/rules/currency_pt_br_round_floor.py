from .interface import Rule
from typing import Union
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from decimal import Decimal, ROUND_FLOOR


class CurrencyBRLRoudingFloor(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.price = self.format_price(product.price)
        product.sale_price = self.format_price(product.sale_price)
        return True

    @staticmethod
    def format_price(price: Union[int, float]) -> str:
        final_price = Decimal(price / 100)
        final_price = final_price.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
        formatted_price = f"{final_price} BRL"
        return formatted_price
