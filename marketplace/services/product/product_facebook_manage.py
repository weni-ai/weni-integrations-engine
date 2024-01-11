from typing import List

from django.contrib.auth import get_user_model

from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from marketplace.wpp_products.models import Product


User = get_user_model()


class ProductFacebookManager:
    def create_or_update_products_on_database(
        self, products: List[FacebookProductDTO], catalog, product_feed
    ):
        products_to_update = []
        products_to_create = []

        for dto in products:
            try:
                product = Product.objects.get(
                    facebook_product_id=dto.id, catalog=catalog
                )  # TODO: Optimize to make a single query at the bank
                product.title = dto.title
                product.description = dto.description
                product.availability = dto.availability
                product.condition = dto.condition
                product.price = dto.price
                product.link = dto.link
                product.image_link = dto.image_link
                product.brand = dto.brand
                product.sale_price = dto.sale_price
                products_to_update.append(product)
            except Product.DoesNotExist:
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

        if products_to_update:
            # Bulk update
            fields_to_update = [
                "title",
                "description",
                "availability",
                "condition",
                "price",
                "link",
                "image_link",
                "brand",
                "sale_price",
            ]
            Product.objects.bulk_update(products_to_update, fields_to_update)

        # Bulk create
        if products_to_create:
            Product.objects.bulk_create(products_to_create)

        return True
