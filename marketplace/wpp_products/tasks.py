import logging

from celery import shared_task

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog
from marketplace.applications.models import App

logger = logging.getLogger(__name__)


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
