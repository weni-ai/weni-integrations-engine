from .interface import Rule
from typing import Union, Optional
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CurrencyCLP(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.price = self.format_price(product.price)
        product.sale_price = self.format_price(product.sale_price)
        return True

    @staticmethod
    def format_price(price: Optional[Union[int, float]]) -> str:
        """
        Format price in CLP currency:
        - Remove last two digits (convert cents to units)
        - Round down to nearest whole number
        - If < 1 CLP and > 0 CLP, return "1 CLP"
        - If None or empty or 0, return "0 CLP"
        """
        if price is None or price == 0:
            return "0 CLP"

        price_in_units = int(price / 100)

        if price_in_units > 0 and price_in_units < 1:
            return "1 CLP"

        if price_in_units == 0:
            return f"{float(price / 100):.2f} CLP"

        final_price = price_in_units / 1000

        return f"{final_price:.3f} CLP"
