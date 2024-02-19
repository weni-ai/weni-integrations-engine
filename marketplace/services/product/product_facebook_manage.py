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
        existing_products = (
            Product.objects.filter(
                facebook_product_id__in=[dto.id for dto in products], catalog=catalog
            )
            .select_related("catalog")
            .in_bulk(field_name="facebook_product_id")
        )

        products_to_update = []
        products_to_create = []

        for dto in products:
            product = existing_products.get(dto.id)
            if product:
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
            else:
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
                    batch_size=1000,
                )

            if products_to_create:
                Product.objects.bulk_create(products_to_create, batch_size=1000)

        return True
