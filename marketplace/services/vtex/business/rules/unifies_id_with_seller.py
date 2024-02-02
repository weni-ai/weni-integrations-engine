from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class UnifiesIdWithSeller(Rule):
    SEPARATOR = "#"

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        seller_id = kwargs.get("seller_id")
        product.id = self.create_unique_product_id(product.id, seller_id)
        return True

    @staticmethod
    def create_unique_product_id(sku_id: str, seller_id: str) -> str:
        return f"{sku_id}{UnifiesIdWithSeller.SEPARATOR}{seller_id}"
