from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class UseRichDescription(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.rich_text_description = self._get_description(product)
        return True

    def _get_description(self, product: FacebookProductDTO) -> str:
        description = (
            product.product_details["ProductDescription"]
            if product.product_details["ProductDescription"] != ""
            else product.product_details["SkuName"]
        )
        return description
