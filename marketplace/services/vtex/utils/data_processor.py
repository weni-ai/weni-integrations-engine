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


@dataclass
class VtexProductDTO:  # TODO: Implement This VtexProductDTO
    pass


class DataProcessor:
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
    def process_product_data(
        skus_ids, active_sellers, service, domain, rules, update_product=False
    ):
        facebook_products = []
        for sku_id in skus_ids:
            product_details = service.get_product_details(sku_id, domain)
            for seller_id in active_sellers:
                availability_details = service.simulate_cart_for_seller(
                    sku_id, seller_id, domain
                )
                if update_product is False and not availability_details["is_available"]:
                    continue

                product_dto = DataProcessor.extract_fields(
                    product_details, availability_details
                )
                params = {"seller_id": seller_id}
                for rule in rules:
                    if not rule.apply(product_dto, **params):
                        break
                else:
                    facebook_products.append(product_dto)

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

    def convert_dtos_to_dicts(dtos: List[FacebookProductDTO]) -> List[dict]:
        return [dataclasses.asdict(dto) for dto in dtos]
