import concurrent.futures
import pandas as pd
import io
import dataclasses
import os
import time

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
    def extract_fields(
        store_domain, product_details, availability_details
    ) -> FacebookProductDTO:
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
        image_url = (
            product_details.get("Images", [])[0].get("ImageUrl")
            if product_details.get("Images")
            else product_details.get("ImageUrl")
        )
        sku_id = product_details["Id"]
        product_url = (
            f"https://{store_domain}{product_details.get('DetailUrl')}?idsku={sku_id}"
        )
        description = (
            product_details["ProductDescription"]
            if product_details["ProductDescription"] != ""
            else product_details["SkuName"]
        )
        return FacebookProductDTO(
            id=sku_id,
            title=product_details["SkuName"].title(),
            description=description.title(),
            availability="in stock"
            if availability_details["is_available"]
            else "out of stock",
            condition="new",
            price=list_price,
            link=product_url,
            image_link=image_url,
            brand=product_details.get("BrandName", "N/A"),
            sale_price=price,
            product_details=product_details,
        )

    @staticmethod
    def process_product_data(
        skus_ids,
        active_sellers,
        service,
        domain,
        store_domain,
        rules,
        update_product=False,
    ):
        num_cpus = os.cpu_count()
        all_facebook_products = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_cpus) as executor:
            futures = [
                executor.submit(
                    DataProcessor.process_single_sku,
                    sku_id,
                    active_sellers,
                    service,
                    domain,
                    store_domain,
                    rules,
                    update_product,
                )
                for sku_id in skus_ids
            ]
            time.sleep(
                15
            )  # TODO: Test whether by waiting this time the processes are terminated correctly
            for future in concurrent.futures.as_completed(futures):
                try:
                    results = future.result()
                    if results:
                        all_facebook_products.extend(results)
                        print("total products extend to", len(all_facebook_products))
                except Exception as e:
                    print(f"Exception in thread: {e}")

        return all_facebook_products

    @staticmethod
    def process_single_sku(
        sku_id, active_sellers, service, domain, store_domain, rules, update_product
    ):
        facebook_products = []
        product_details = service.get_product_details(sku_id, domain)
        for seller_id in active_sellers:
            availability_details = service.simulate_cart_for_seller(
                sku_id, seller_id, domain
            )
            if update_product is False and not availability_details["is_available"]:
                continue

            product_dto = DataProcessor.extract_fields(
                store_domain, product_details, availability_details
            )
            params = {"seller_id": seller_id}
            all_rules_applied = True
            for rule in rules:
                if not rule.apply(product_dto, **params):
                    all_rules_applied = False
                    break

            if all_rules_applied:
                facebook_products.append(product_dto)

        return facebook_products

    def products_to_csv(products: List[FacebookProductDTO]) -> io.BytesIO:
        product_dicts = [dataclasses.asdict(product) for product in products]
        df = pd.DataFrame(product_dicts)
        df = df.drop(columns=["product_details"])
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)
        return buffer

    def clear_csv_buffer(buffer: io.BytesIO):
        buffer.close()

    def convert_dtos_to_dicts_list(dtos: List[FacebookProductDTO]) -> List[dict]:
        dicts_list = []
        for dto in dtos:
            dto_dict = dataclasses.asdict(dto)
            dto_dict.pop("product_details", None)
            dicts_list.append(dto_dict)

        return dicts_list
