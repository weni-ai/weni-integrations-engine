from .interface import Rule
from typing import Union
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CurrencyBRL(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.price = self.format_price(product.price)
        product.sale_price = self.format_price(product.sale_price)
        return True

    @staticmethod
    def format_price(price: Union[int, float]) -> str:
        formatted_price = f"{price / 100:.2f} BRL"
        return formatted_price
