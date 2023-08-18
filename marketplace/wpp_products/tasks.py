import logging

from celery import shared_task

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Product, ProductFeed, Catalog
from marketplace.accounts.models import User
from marketplace.applications.models import App

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


@shared_task(name="sync_facebook_catalogs")
def sync_facebook_catalogs():
    apps = App.objects.filter(code="wpp-cloud")
    client = FacebookClient()

    for app in apps:
        wa_business_id = app.config.get("wa_business_id")
        wa_waba_id = app.config.get("wa_waba_id")

        if wa_business_id and wa_waba_id:
            local_catalog_ids = set(
                app.catalogs.values_list("facebook_catalog_id", flat=True)
            )

            response = client.list_all_catalogs(wa_business_id=wa_business_id)
            fba_catalogs_ids = set(response)

            to_create = fba_catalogs_ids - local_catalog_ids
            to_delete = local_catalog_ids - fba_catalogs_ids

            for catalog_id in to_create:
                details = client.get_catalog_details(catalog_id)
                try:
                    Catalog.objects.create(
                        app=app,
                        facebook_catalog_id=details["id"],
                        name=details["name"],
                        category=details["vertical"],
                    )
                except Exception as e:
                    logger.error(
                        f"Error creating catalog for app {app.uuid}: {str(e)} , object: {details}"
                    )
                    continue

            if to_delete:
                app.catalogs.filter(facebook_catalog_id__in=to_delete).delete()
