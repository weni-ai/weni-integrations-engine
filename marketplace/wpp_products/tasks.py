import logging

from celery import shared_task

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Product, ProductFeed
from marketplace.accounts.models import User

logger = logging.getLogger(__name__)


@shared_task(name="create_products_by_feed")
def create_products_by_feed(**kwargs):
    product_feed_uuid = kwargs.get("product_feed_uuid")
    products_on_file = kwargs.get("file_products")
    user_email = kwargs.get("user_email")

    product_feed = ProductFeed.objects.get(uuid=product_feed_uuid)
    user = User.objects.get(email=user_email)

    feed_id = product_feed.facebook_feed_id

    client = FacebookClient()

    response = client.get_upload_status(feed_id=feed_id)

    if response is not True:
        logger.error(f"Error retrieving upload status: {response}")
        return (
            f"Failed to create products by feed due to upload status error: {response}"
        )

    products_on_fb = client.list_all_products_by_feed(feed_id=feed_id)

    if not products_on_fb:
        return "No products found on Facebook."

    for fb_product in products_on_fb:
        retailer_id = fb_product.get("retailer_id")

        if retailer_id in products_on_file:
            matching_product = products_on_file[retailer_id]
            if matching_product:
                Product.objects.create(
                    facebook_product_id=fb_product["id"],
                    product_retailer_id=retailer_id,
                    title=fb_product["name"],
                    description=matching_product["description"],
                    availability=matching_product["availability"],
                    condition=matching_product["condition"],
                    price=matching_product["price"],
                    link=matching_product["link"],
                    image_link=matching_product["image_link"],
                    brand=matching_product["brand"],
                    feed=product_feed,
                    catalog=product_feed.catalog,
                    created_by=user,
                )
