from typing import List

from django.db import transaction

from marketplace.services.vtex.utils.data_processor import FacebookProductDTO
from marketplace.wpp_products.models import Product


class ProductFacebookManager:
    def save_products_on_database(
        self, products: List[FacebookProductDTO], catalog, product_feed
    ):
        product_instances = [
            Product(
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
                created_by=catalog.created_by,
                feed=product_feed,
            )
            for dto in products
        ]

        with transaction.atomic():
            Product.objects.bulk_create(product_instances)
