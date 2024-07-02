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

            # current_description = product.description
            specifications = self._product_specification(product, service, domain)
            combined_description = f"{product.description}\n{specifications}"

            # Ensure the combined description does not exceed 9999 characters
            if len(combined_description) > 9999:
                combined_description = combined_description[:9999]

            product.description = combined_description

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
        specification_text = "Características: "
        specifications = service.get_product_specification(product_id, domain)

        specification_parts = []
        for specification in specifications:
            name = specification.get("Name")
            value = ", ".join(specification.get("Value", []))
            specification_parts.append(f"{name} - {value}")

        specification_text += "\n ".join(specification_parts) + "."
        return specification_text
