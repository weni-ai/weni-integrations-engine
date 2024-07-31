from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class SetDefaultImageURL(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        image_url = product.product_details.get("ImageUrl")
        if image_url:
            product.image_link = image_url
        return True
