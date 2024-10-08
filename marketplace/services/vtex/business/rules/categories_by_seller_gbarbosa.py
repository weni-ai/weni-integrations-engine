from .interface import Rule
from typing import Union
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CategoriesBySeller(Rule):
    HOME_APPLIANCES_CATEGORIES = {"eletrodoméstico", "eletro", "eletroportáteis"}
    DESCRIPTION_MAX_LENGTH = 9999

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        seller_id = kwargs.get("seller_id")
        service = kwargs.get("service")
        domain = kwargs.get("domain")

        if self._is_home_appliance(product):
            if seller_id != "gbarbosab101":
                return False

            specifications = self._product_specification(product, service, domain)

            combined_description = f"{product.description}\n{specifications}"
            combined_rich_text_description = (
                f"{self._product_description(product)}\n{specifications}"
            )

            product.description = self._truncate_text(
                combined_description, self.DESCRIPTION_MAX_LENGTH
            )
            product.rich_text_description = self._truncate_text(
                combined_rich_text_description, self.DESCRIPTION_MAX_LENGTH
            )

            self._fetch_and_update_pix_price(product, service, seller_id, domain)

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

        specification_text = "\n\n*Características:*\n\n"
        specifications = service.get_product_specification(product_id, domain)

        specification_parts = []

        for specification in specifications:
            values = [
                value for value in specification.get("Value", []) if value != "CD"
            ]

            if values:
                specification_parts.append(
                    f"*{specification.get('Name')}* : {', '.join(values)}"
                )

        specification_text += "\n".join(specification_parts) + "."
        return specification_text

    def _product_description(self, product: FacebookProductDTO) -> str:
        return (
            product.product_details.get("ProductDescription")
            or product.product_details["SkuName"]
        )

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        return text[:max_length] if len(text) > max_length else text

    def _fetch_and_update_pix_price(
        self, product: FacebookProductDTO, service, seller_id, domain
    ):
        availability_details = service.simulate_cart_for_seller(
            product.product_details.get("Id"), seller_id, domain
        )
        is_available = availability_details.get("is_available")

        if is_available:
            pix_value = self._extract_pix_value(availability_details)
            current_sale_price = product.sale_price or product.price

            if pix_value and pix_value < current_sale_price:
                self._append_pix_promotion_description(
                    product, pix_value, current_sale_price
                )
                product.sale_price = pix_value
            elif not product.sale_price:
                product.sale_price = current_sale_price

    def _extract_pix_value(self, availability_details: dict) -> float:
        data = availability_details.get("data", {})
        payment_data = data.get("paymentData", {})
        installment_options = payment_data.get("installmentOptions", [])

        for payment in installment_options:
            if payment.get("paymentName", "").upper() == "PIX":
                installments = payment.get("installments", [])
                if installments:
                    return installments[0].get("value")
        return None

    def _append_pix_promotion_description(
        self, product: FacebookProductDTO, pix_value, sale_price
    ):
        pix_description = (
            f"*Preço promocional PIX R$ {self._format_price(pix_value)} ou "
            f"R$ {self._format_price(sale_price)} em outras modalidades de pagamento*\n\n"
        )
        product.description = pix_description + product.description
        product.rich_text_description = product.description

    def _format_price(self, price: Union[int, float]) -> str:
        formatted_price = (
            f"{price / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )
        return formatted_price
