from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction

from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.wpp_products.models import (
    UploadProduct,
    Catalog,
)


User = get_user_model()


class ProductFacebookManager:
    def save_batch_product_data(
        self,
        products_dto: List[FacebookProductDTO],
        catalog: Catalog,
    ):
        """
        Save or update products in batch format for the new process.

        This method processes each product individually, updating existing records
        or creating new ones as needed. It handles exceptions for each product
        separately to ensure partial success is possible.

        Args:
            products_dto: List of FacebookProductDTO objects containing product data
            catalog: The Catalog object to associate with the products

        Returns:
            bool: True if all products were saved successfully, False otherwise
        """
        all_success = True
        print(
            f"Starting insertion process for {len(products_dto)} products (Batch). Catalog: {catalog.name}"
        )
        for product in products_dto:
            facebook_product_id = product.id
            try:
                UploadProduct.objects.update_or_create(
                    facebook_product_id=facebook_product_id,
                    catalog=catalog,
                    defaults={"data": product.to_meta_payload(), "status": "pending"},
                )
            except Exception as e:
                print(f"Failed to save or update product: {str(e)}")
                all_success = False

        UploadProduct.remove_duplicates(catalog)
        return all_success

    def bulk_save_initial_product_data(
        self, products_dto: List[FacebookProductDTO], catalog: Catalog
    ):
        """
        Save products in bulk for the initial insertion process.

        This method uses Django's bulk_create for efficient database operations
        during the initial product load. All operations are wrapped in a transaction
        to ensure atomicity - either all products are saved or none.

        Args:
            products_dto: List of FacebookProductDTO objects containing product data
            catalog: The Catalog object to associate with the products

        Returns:
            bool: True if all products were saved successfully, False otherwise
        """
        all_success = True
        print(
            f"Starting bulk insertion process for {len(products_dto)} products. Catalog: {catalog.name}"
        )

        new_products = [
            UploadProduct(
                facebook_product_id=product.id,
                catalog=catalog,
                data=product.to_meta_payload(),
                status="pending",
            )
            for product in products_dto
        ]

        try:
            with transaction.atomic():
                UploadProduct.objects.bulk_create(new_products, batch_size=5000)
            print(
                f"All {len(products_dto)} products were saved successfully in the database."
            )
        except Exception as e:
            print(f"Failed to save products during bulk initial insertion: {str(e)}")
            all_success = False

        UploadProduct.remove_duplicates(catalog)
        return all_success
