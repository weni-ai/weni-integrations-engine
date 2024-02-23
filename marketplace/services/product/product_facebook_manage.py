from typing import List

from django.contrib.auth import get_user_model
from django.db import transaction

from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from marketplace.wpp_products.models import Product


User = get_user_model()


class ProductFacebookManager:
    def create_or_update_products_on_database(
        self, products: List[FacebookProductDTO], catalog, product_feed
    ):
        print("Starting the data insertion process in integrations databases")

        # Initialize dictionaries to map existing products
        existing_products_map = {}

        # Search all relevant products at once based on the specified catalog
        existing_products_qs = Product.objects.filter(
            facebook_product_id__in=[dto.id for dto in products], catalog=catalog
        )

        # Update the mapping using the combination of facebook_product_id and catalog_id
        for product in existing_products_qs:
            existing_products_map[
                (product.facebook_product_id, product.catalog_id)
            ] = product

        products_to_update = []
        products_to_create = []

        for dto in products:
            key = (dto.id, catalog.id)  # Combination of ID and catalog_id as key
            existing_product = existing_products_map.get(key)

            if existing_product:
                # Update existing product
                existing_product.title = dto.title
                existing_product.description = dto.description
                existing_product.availability = dto.availability
                existing_product.condition = dto.condition
                existing_product.price = dto.price
                existing_product.link = dto.link
                existing_product.image_link = dto.image_link
                existing_product.brand = dto.brand
                existing_product.sale_price = dto.sale_price
                products_to_update.append(existing_product)
            else:
                # Prepare a new product for creation
                new_product = Product(
                    facebook_product_id=dto.id,
                    title=dto.title,
                    description=dto.description,
                    availability=dto.availability,
                    condition=dto.condition,
                    price=dto.price,
                    link=dto.link,
                    image_link=dto.image_link,
                    brand=dto.brand,
                    sale_price=dto.sale_price,
                    catalog=catalog,
                    created_by=User.objects.get_admin_user(),
                    feed=product_feed,
                )
                products_to_create.append(new_product)

        # Bulk processing to update and create
        with transaction.atomic():
            if products_to_update:
                Product.objects.bulk_update(
                    products_to_update,
                    [
                        "title",
                        "description",
                        "availability",
                        "condition",
                        "price",
                        "link",
                        "image_link",
                        "brand",
                        "sale_price",
                    ],
                    batch_size=10000,
                )
                print(
                    f"{len(products_to_update)} products have been updated in the integration databases"
                )

            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=10000)
                print(
                    f"{len(products_to_create)} products have been created in the integration databases"
                )

        return True
