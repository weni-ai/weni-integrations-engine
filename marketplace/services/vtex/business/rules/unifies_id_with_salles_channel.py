import logging

from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO

logger = logging.getLogger(__name__)


class UnifiesIdWithSallesChannel(Rule):
    SEPARATOR = "#"

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        salles_channel = kwargs.get("salles_channel")
        if not salles_channel:
            logger.info(
                "No salles_channel found, skipping unifies_id_with_salles_channel"
            )
            return False

        product.id = self.unifies_product_id_seller_channel(product.id, salles_channel)
        return True

    @staticmethod
    def unifies_product_id_seller_channel(product_id: str, salles_channel: str) -> str:
        return f"{product_id}{UnifiesIdWithSallesChannel.SEPARATOR}{salles_channel}"
