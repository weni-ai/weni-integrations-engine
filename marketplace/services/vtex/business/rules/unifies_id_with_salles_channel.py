import logging

from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO

logger = logging.getLogger(__name__)


class UnifiesIdWithSallesChannel(Rule):
    SEPARATOR = "#"

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        sales_channel = kwargs.get("sales_channel")
        if not sales_channel:
            logger.info(
                "No sales_channel found, skipping unifies_id_with_sales_channel"
            )
            return False

        product.id = self.unifies_product_id_seller_channel(product.id, sales_channel)
        return True

    @staticmethod
    def unifies_product_id_seller_channel(
        product_id: str, sales_channel: list[str]
    ) -> str:
        return f"{product_id}{UnifiesIdWithSallesChannel.SEPARATOR}{sales_channel}"
