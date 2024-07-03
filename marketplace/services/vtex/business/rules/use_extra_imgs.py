from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class UseExtraImgs(Rule):
    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        product.additional_image_link = self._get_images(product)
        return True

    def _get_images(self, product: FacebookProductDTO) -> str:
        images_str_list = ""

        images = product.product_details.get("Images", [])
        if len(images) > 1:
            images.pop(0)  # Remove the first element

            for image in images:
                image_url = image.get("ImageUrl")
                # Add the URL and a comma only if it does not exceed 2000 characters
                if len(images_str_list) + len(image_url) + 1 <= 2000:
                    if images_str_list:
                        images_str_list += "," + image_url
                    else:
                        images_str_list = image_url
                else:
                    break

        return images_str_list
