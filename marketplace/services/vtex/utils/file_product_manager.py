import csv
import pandas as pd
import io

from typing import List

from dataclasses import asdict

from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO


class FileProductManager:
    @staticmethod
    def products_to_csv(products: List[FacebookProductDTO]) -> io.BytesIO:
        print("Generating CSV file")
        product_dicts = [asdict(product) for product in products]
        df = pd.DataFrame(product_dicts)
        df = df.drop(columns=["product_details"])
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)
        print("CSV file successfully generated in memory")
        return buffer

    @staticmethod
    def product_to_csv_line(product: FacebookProductDTO) -> str:
        def escape_quotes(text: str) -> str:
            """Replaces quotes with a empty space in the provided text."""
            if isinstance(text, str):
                text = text.replace('"', "").replace("'", " ")
            return text

        product_dict = asdict(product)
        product_dict.pop(
            "product_details", None
        )  # Remove 'product_details' field if present

        cleaned_product_dict = {k: escape_quotes(v) for k, v in product_dict.items()}

        df = pd.DataFrame([cleaned_product_dict])
        csv_line = df.to_csv(
            index=False, header=False, encoding="utf-8", quoting=csv.QUOTE_MINIMAL
        ).strip()
        return csv_line

    @staticmethod
    def clear_csv_buffer(buffer: io.BytesIO):
        buffer.close()

    @staticmethod
    def convert_dtos_to_dicts_list(dtos: List[FacebookProductDTO]) -> List[dict]:
        print("Converting DTO's into dictionary.")
        dicts_list = []
        for dto in dtos:
            dto_dict = asdict(dto)
            dto_dict.pop("product_details", None)
            dicts_list.append(dto_dict)

        print("Products successfully converted to dictionary.")
        return dicts_list
