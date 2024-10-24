from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction

from marketplace.wpp_products.models import (
    UploadProduct,
    Catalog,
    ProductFeed,
)
from marketplace.services.vtex.utils.data_processor import (
    DataProcessor,
    FacebookProductDTO,
)


User = get_user_model()


class ProductFacebookManager:
    def save_csv_product_data(
        self,
        products_dto: List[FacebookProductDTO],
        catalog: Catalog,
        product_feed: ProductFeed,
        data_processor: DataProcessor,
    ):
        all_success = True
        print(
            f"Starting insertion process for {len(products_dto)} products. Catalog: {catalog.name}"
        )
        for product in products_dto:
            facebook_product_id = product.id
            product_csv = data_processor.product_to_csv_line(product)

            try:
                product, _ = UploadProduct.objects.update_or_create(
                    facebook_product_id=facebook_product_id,
                    catalog=catalog,
                    feed=product_feed,
                    defaults={
                        "data": product_csv,
                        "status": "pending",
                    },
                )
            except Exception as e:
                print(f"Failed to save or update product: {str(e)}")
                all_success = False

        # Call duplicate cleanup after processing
        UploadProduct.remove_duplicates(catalog)

        print(
            f"All {len(products_dto)} products were saved successfully in the database:"
            f"Catalog ID {catalog.facebook_catalog_id}, "
            f"Feed ID {product_feed.facebook_feed_id}, Product Facebook ID {facebook_product_id}"
        )
        return all_success

    def save_first_csv_product_data(
        self,
        products_dto: List[FacebookProductDTO],
        catalog: Catalog,
        product_feed: ProductFeed,
        data_processor: DataProcessor,
    ):
        print("Starting the initial data insertion process in UploadProduct")

        # Step 1: Delete existing products for the catalog
        deleted_count, _ = UploadProduct.objects.filter(catalog=catalog).delete()
        print(
            f"Deleted {deleted_count} existing products for catalog {catalog.facebook_catalog_id}"
        )

        # Step 2: Prepare data for bulk create
        products_to_create = []
        batch_size = 30000  # Define the batch size for bulk creation

        for dto in products_dto:
            product_csv = data_processor.product_to_csv_line(dto)
            new_product = UploadProduct(
                facebook_product_id=dto.id,
                data=product_csv,
                catalog=catalog,
                feed=product_feed,
                status="pending",
            )
            products_to_create.append(new_product)

            # Bulk create in batches
            if len(products_to_create) >= batch_size:
                UploadProduct.objects.bulk_create(
                    products_to_create, batch_size=batch_size
                )
                print(f"Bulk created {len(products_to_create)} products.")
                products_to_create.clear()  # Clear the list after bulk creation

        # If remaining products, create
        if products_to_create:
            UploadProduct.objects.bulk_create(products_to_create, batch_size=batch_size)
            print(f"Bulk created {len(products_to_create)} remaining products.")

        # Call duplicate cleanup after processing
        UploadProduct.remove_duplicates(catalog)

        print("Initial data insertion process completed successfully.")
        return True

    def bulk_save_csv_product_data(
        self,
        products_dto: List[FacebookProductDTO],
        catalog: Catalog,
        product_feed: ProductFeed,
        data_processor: DataProcessor,
        batch_size: int = 30000,
    ):
        print(
            f"Starting insertion process for {len(products_dto)} products. Catalog: {catalog.name}"
        )

        # Fetch products matching facebook_product_id from products_dto, regardless of status
        existing_products = UploadProduct.objects.filter(
            facebook_product_id__in=[product.id for product in products_dto],
            catalog=catalog,
            feed=product_feed,
        )

        # Create a dictionary of existing products for easy access
        existing_products_dict = {
            product.facebook_product_id: product for product in existing_products
        }

        new_products = []
        update_products = []

        for product in products_dto:
            facebook_product_id = product.id
            product_csv = data_processor.product_to_csv_line(product)

            if facebook_product_id in existing_products_dict:
                # Update existing product
                existing_product = existing_products_dict[facebook_product_id]
                existing_product.data = product_csv
                existing_product.status = "pending"
                update_products.append(existing_product)
            else:
                # Create new product
                new_products.append(
                    UploadProduct(
                        facebook_product_id=facebook_product_id,
                        catalog=catalog,
                        feed=product_feed,
                        data=product_csv,
                        status="pending",
                    )
                )

        all_success = True
        try:
            with transaction.atomic():
                if new_products:
                    UploadProduct.objects.bulk_create(
                        new_products, batch_size=batch_size
                    )
                if update_products:
                    UploadProduct.objects.bulk_update(
                        update_products, ["data", "status"], batch_size=batch_size
                    )

            print(
                f"All {len(products_dto)} products were saved successfully in the database."
            )
            print(
                f"New products: {len(new_products)}, Updateds : {len(update_products)}"
            )
            print(
                f"Catalog ID {catalog.facebook_catalog_id}, Feed ID {product_feed.facebook_feed_id}"
            )

        except Exception as e:
            print(f"Failed to save or update products: {str(e)}")
            all_success = False

        # Call duplicate cleanup after processing
        UploadProduct.remove_duplicates(catalog)

        return all_success
