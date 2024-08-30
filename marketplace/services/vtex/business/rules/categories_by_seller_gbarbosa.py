from .interface import Rule
from marketplace.services.vtex.utils.data_processor import FacebookProductDTO


class CategoriesBySeller(Rule):
    HOME_APPLIANCES_CATEGORIES = {"eletrodoméstico", "eletro", "eletroportáteis"}
    DESCRIPTION_MAX_LENGTH = 9999

    def __init__(self):
        self.sku = None
        self.seller_id = None
        self.domain = None
        self.service = None

    def apply(self, product: FacebookProductDTO, **kwargs) -> bool:
        self.seller_id = kwargs.get("seller_id")
        self.service = kwargs.get("service")
        self.domain = kwargs.get("domain")

        if self._is_home_appliance(product):
            if self.seller_id != "gbarbosab101":
                return False

            specifications = self._product_specification(product)

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

            self._fetch_and_update_pix_price(product)

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

    def _product_specification(self, product: FacebookProductDTO) -> str:
        self.sku = product.product_details.get("Id")
        product_id = product.product_details.get("ProductId")

        specification_text = "\n\n*Características:*\n\n"
        specifications = self.service.get_product_specification(product_id, self.domain)

        specification_parts = [
            f"*{specification.get('Name')}* : {', '.join(specification.get('Value', []))}"
            for specification in specifications
            if specification.get("Value")
        ]

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

    def _fetch_and_update_pix_price(self, product: FacebookProductDTO):
        availability_details = self.service.simulate_cart_for_seller(
            self.sku, self.seller_id, self.domain
        )
        is_available = availability_details.get("is_available")

        if is_available:
            pix_value = self._extract_pix_value(availability_details)
            if pix_value:
                product.sale_price = pix_value
                self._append_pix_promotion_description(product)

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

    def _append_pix_promotion_description(self, product: FacebookProductDTO):
        pix_description = "*Preço promocional para o pagamento no pix*\n"
        product.description = pix_description + product.description
