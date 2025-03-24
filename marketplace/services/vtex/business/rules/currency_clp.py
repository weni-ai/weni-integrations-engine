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
        - Convert from cents to CLP
        - Truncate decimals (no rounding)
        - Force price to end with .990
        - If < 1 CLP, return "1 CLP"
        - If None or empty, return "0 CLP"
        """
        # Check if price is None or empty
        if price is None:
            return "0 CLP"

        # Convert cents to CLP
        price_in_units = price / 100

        # Truncate to integer (no rounding)
        truncated_units = int(price_in_units)

        # If less than 1, return 1 CLP
        if truncated_units < 1:
            return "1 CLP"

        # Add .990 to force the correct ending
        final_price = truncated_units + 0.990

        return f"{final_price:.3f} CLP"
