import csv
import io
import dataclasses

from dataclasses import dataclass

from typing import List


@dataclass
class FacebookProductDTO:
    id: str
    title: str
    description: str
    availability: str
    condition: str
    price: str
    link: str
    image_link: str
    brand: str
    sale_price: str
    product_details: dict  # TODO: Implement ProductDetailsDTO

    def get_multiplier(self):
        return self.product_details.get("UnitMultiplier", 1.0)

    def get_weight(self):
        return self.product_details["Dimension"]["weight"]

    def calculates_by_weight(self):
        return self.product_details["MeasurementUnit"] != "un"


@dataclass
class VtexProductDTO:  # TODO: Implement This VtexProductDTO
    pass


class DataProcessor:
    SEPARATOR = "#"
    CURRENCY = "BRL"

    @staticmethod
    def create_unique_product_id(sku_id, seller_id):
        return f"{sku_id}{DataProcessor.SEPARATOR}{seller_id}"

    @staticmethod
    def decode_unique_product_id(unique_product_id):
        sku_id, seller_id = unique_product_id.split(DataProcessor.SEPARATOR)
        return sku_id, seller_id

    @staticmethod
    def extract_fields(product_details, availability_details) -> FacebookProductDTO:
        price = (
            availability_details["price"]
            if availability_details["price"] is not None
            else 0
        )
        list_price = (
            availability_details["list_price"]
            if availability_details["list_price"] is not None
            else 0
        )
        return FacebookProductDTO(
            id=product_details["Id"],
            title=product_details["SkuName"],
            description=product_details["SkuName"],
            availability="in stock"
            if availability_details["is_available"]
            else "out of stock",
            condition="new",
            price=list_price,
            link="",  # TODO: Needs Implement This based on FacebookAPI
            image_link=product_details["ImageUrl"],
            brand=product_details.get("BrandName", "N/A"),
            sale_price=price,
            product_details=product_details,
        )

    @staticmethod
    def format_price(price):
        """Formats the price to the standard 'XX.XX BRL'."""
        formatted_price = f"{price / 100:.2f} {DataProcessor.CURRENCY}"  # TODO: Move CURRENCY to business layer
        return formatted_price

    @staticmethod
    def format_fields(
        seller_id, product: FacebookProductDTO
    ):  # TODO: Move this method rules to business layer
        if product.calculates_by_weight():
            # Apply price calculation logic per weight/unit
            DataProcessor.calculate_price_by_weight(product)

        # Format the price for all products
        product.price = DataProcessor.format_price(product.price)
        product.sale_price = DataProcessor.format_price(product.sale_price)
        product.id = DataProcessor.create_unique_product_id(product.id, seller_id)

        return product

    @staticmethod
    def calculate_price_by_weight(product: FacebookProductDTO):
        unit_multiplier = product.get_multiplier()
        product_weight = product.get_weight()
        weight = product_weight * unit_multiplier
        product.price = product.price * unit_multiplier
        product.sale_price = product.sale_price * unit_multiplier
        product.description += f" - {weight}g"

    @staticmethod
    def process_product_data(
        skus_ids, active_sellers, service, domain, update_product=False
    ):
        facebook_products = []
        for sku_id in skus_ids:
            product_details = service.get_product_details(sku_id, domain)

            for seller_id in active_sellers:
                availability_details = service.simulate_cart_for_seller(
                    sku_id, seller_id, domain
                )

                if update_product is False:
                    if not availability_details["is_available"]:
                        continue

                extracted_product_dto = DataProcessor.extract_fields(
                    product_details, availability_details
                )
                formatted_product_dto = DataProcessor.format_fields(
                    seller_id, extracted_product_dto
                )
                facebook_products.append(formatted_product_dto)

        return facebook_products

    def products_to_csv(products: List[FacebookProductDTO]) -> str:
        output = io.StringIO()
        fieldnames = [
            field.name
            for field in dataclasses.fields(FacebookProductDTO)
            if field.name != "product_details"
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for product in products:
            row = dataclasses.asdict(product)
            row.pop(
                "product_details", None
            )  # TODO: should change this logic before going to production
            writer.writerow(row)

        return output.getvalue()

    @staticmethod
    def generate_csv_file(csv_content: str) -> io.BytesIO:
        csv_bytes = csv_content.encode("utf-8")
        csv_memory = io.BytesIO(csv_bytes)
        return csv_memory
