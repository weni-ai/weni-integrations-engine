from .interface import Rule
from typing import Union, Optional
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CurrencyARS(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.price = self.format_price(product.price)
        product.sale_price = self.format_price(product.sale_price)
        return True

    @staticmethod
    def format_price(price: Optional[Union[int, float]]) -> str:
        """
        Format price in ARS currency:
        - Remove last two digits (ignore cents)
        """
        if price is None or price == 0:
            return "0 ARS"

        price_no_cents = int(price / 100)

        if price_no_cents == 0:
            return "1 ARS"

        return f"{price_no_cents} ARS"
