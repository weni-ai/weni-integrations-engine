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
    """
    Manages Facebook product operations, including batch processing and priority handling.

    This class is responsible for managing the operations related to Facebook products,
    such as setting batch sizes for processing and handling priority levels for product
    operations.
    """

    def __init__(self, batch_size: int = 10_000, priority: int = 0):
        """
        Initialize the ProductFacebookManager with specified batch size and priority.

        Args:
            batch_size: The number of products to process in each batch. This determines
                        how many items will be handled at a time during operations.
            priority: The priority level for processing products. This can be used to
                      order the products during processing.
        """
        self.batch_size = batch_size
        self.priority = priority

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
                priority=self.priority,
            )
            for product in products_dto
        ]

        try:
            with transaction.atomic():
                UploadProduct.objects.bulk_create(
                    new_products, batch_size=self.batch_size
                )
            print(
                f"All {len(products_dto)} products were saved successfully in the database."
            )
        except Exception as e:
            print(f"Failed to save products during bulk initial insertion: {str(e)}")
            all_success = False

        UploadProduct.remove_duplicates(catalog)
        return all_success
