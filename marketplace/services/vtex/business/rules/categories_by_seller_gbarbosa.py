from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CategoriesBySeller(Rule):
    HOME_APPLIANCES_CATEGORIES = {"eletrodoméstico", "eletro", "eletroportáteis"}

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        seller_id = kwargs.get("seller_id")
        service = kwargs.get("service")
        domain = kwargs.get("domain")

        if self._is_home_appliance(product):
            # Only seller gbarbosab101 can have appliances
            if seller_id != "gbarbosab101":
                return False

            specifications = self._product_specification(product, service, domain)

            combined_description = f"{product.description}\n{specifications}"
            combined_rich_text_description = (
                f"{self._product_description(product)}\n{specifications}"
            )

            # Ensure the combined description does not exceed 9999 characters
            product.description = self._truncate_text(combined_description, 9999)
            product.rich_text_description = self._truncate_text(
                combined_rich_text_description, 9999
            )

        # If the product is not an appliance, it can be added by any seller
        return True

    def _get_categories(self, product: FacebookProductDTO) -> set:
        return set(
            category.lower()
            for category in product.product_details.get(
                "ProductCategories", {}
            ).values()
        )

    def _is_home_appliance(self, product: FacebookProductDTO) -> bool:
        product_categories = self._get_categories(product)
        return bool(self.HOME_APPLIANCES_CATEGORIES.intersection(product_categories))

    def _product_specification(
        self, product: FacebookProductDTO, service, domain
    ) -> str:
        product_id = product.product_details.get("ProductId")
        specification_text = "<br><br><b>Características:</b><br><br>"
        specifications = service.get_product_specification(product_id, domain)

        specification_parts = []
        for specification in specifications:
            name = specification.get("Name")
            value = ", ".join(specification.get("Value", []))
            if value:
                specification_parts.append(f"<b>{name}</b> : {value}")

        specification_text += "<br>".join(specification_parts) + "."
        return specification_text

    def _product_description(self, product: FacebookProductDTO) -> str:
        description = (
            product.product_details["ProductDescription"]
            if product.product_details["ProductDescription"] != ""
            else product.product_details["SkuName"]
        )
        return description

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        """Truncates text to the maximum specified length."""
        if len(text) > max_length:
            return text[:max_length]
        return text
