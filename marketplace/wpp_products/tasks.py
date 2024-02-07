import logging

from celery import shared_task

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import Catalog
from marketplace.clients.flows.client import FlowsClient
from marketplace.celery import app as celery_app
from marketplace.services.vtex.generic_service import VtexService
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.services.flows.service import FlowsService
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App

from django_redis import get_redis_connection


logger = logging.getLogger(__name__)


SYNC_WHATSAPP_CATALOGS_LOCK_KEY = "sync-whatsapp-catalogs-lock"


@shared_task(name="sync_facebook_catalogs")
def sync_facebook_catalogs():
    apptype = APPTYPES.get("wpp-cloud")
    for app in apptype.apps:
        service = FacebookCatalogSyncService(app)
        service.sync_catalogs()


class FacebookCatalogSyncService:
    SYNC_WHATSAPP_CATALOGS_LOCK_KEY = "sync-whatsapp-catalogs-lock"

    def __init__(self, app):
        self.app = app
        self.client = FacebookClient(app.apptype.get_access_token(app))
        self.flows_client = FlowsClient()
        self.redis = get_redis_connection()

    def sync_catalogs(self):
        if self.redis.get(self.SYNC_WHATSAPP_CATALOGS_LOCK_KEY):
            print("The catalogs are already syncing by another task!")
            return

        with self.redis.lock(self.SYNC_WHATSAPP_CATALOGS_LOCK_KEY):
            wa_business_id = self.app.config.get("wa_business_id")
            wa_waba_id = self.app.config.get("wa_waba_id")

            if not (wa_business_id and wa_waba_id):
                print(f"Business ID or WABA ID missing for app: {self.app.uuid}")
                return

            try:
                local_catalog_ids = set(
                    self.app.catalogs.values_list("facebook_catalog_id", flat=True)
                )
                all_catalogs_id, all_catalogs = self._list_all_catalogs()

                if all_catalogs_id:
                    self._update_catalogs_on_flows(all_catalogs)
                    self._sync_local_catalogs(all_catalogs_id, local_catalog_ids)
            except Exception as e:
                logger.error(f"Error during sync process for App {self.app.name}: {e}")

    def _list_all_catalogs(self):
        try:
            return self.client.list_all_catalogs(self.app.config.get("wa_business_id"))
        except Exception as e:
            logger.error(f"Error on list all catalogs for App: {str(e)}")
            return [], []

    def _update_catalogs_on_flows(self, all_catalogs):
        try:
            self.flows_client.update_catalogs(
                str(self.app.flow_object_uuid), all_catalogs
            )
        except Exception as e:
            logger.error(
                f"Error updating catalogs on flows for App: {self.app.uuid} error: {str(e)}"
            )

    def _sync_local_catalogs(self, all_catalogs_id, local_catalog_ids):
        fba_catalogs_ids = set(all_catalogs_id)
        to_create = fba_catalogs_ids - local_catalog_ids
        to_delete = local_catalog_ids - fba_catalogs_ids

        for catalog_id in to_create:
            try:
                details = self.client.get_catalog_details(catalog_id)
                if details:
                    Catalog.objects.create(
                        app=self.app,
                        facebook_catalog_id=details["id"],
                        name=details["name"],
                        category=details["vertical"],
                    )
            except Exception as e:
                logger.error(f"Error creating catalog {catalog_id} for App: {str(e)}")
                # Continues with the next catalog_id

        if to_delete:
            self.app.catalogs.filter(facebook_catalog_id__in=to_delete).delete()

        print(f"Success in synchronizing the app's catalogs for app: {self.app.uuid}")


@celery_app.task(name="task_insert_vtex_products")
def task_insert_vtex_products(**kwargs):
    vtex_service = VtexService()
    flows_service = FlowsService(FlowsClient())

    credentials = kwargs.get("credentials")
    catalog_uuid = kwargs.get("catalog_uuid")

    catalog = Catalog.objects.get(uuid=catalog_uuid)
    try:
        api_credentials = APICredentials(
            app_key=credentials.get("app_key"),
            app_token=credentials.get("app_token"),
            domain=credentials.get("domain"),
        )

        products = vtex_service.first_product_insert(api_credentials, catalog)
        dict_catalog = {
            "name": catalog.name,
            "facebook_catalog_id": catalog.facebook_catalog_id,
        }
        flows_service.update_vtex_products(
            products, str(catalog.app.flow_object_uuid), dict_catalog
        )
        print("Products created and sent to flows successfully")
    except Exception as e:
        logger.error(
            f"Error on insert vtex products for catalog {str(catalog.uuid)}, {e}"
        )


@celery_app.task(name="task_update_vtex_products")
def task_update_vtex_products(**kwargs):
    vtex_service = VtexService()
    flows_service = FlowsService(FlowsClient())

    app_uuid = kwargs.get("app_uuid")
    webhook_data = kwargs.get("webhook_data")

    try:
        vtex_app = App.objects.get(uuid=app_uuid, configured=True, code="vtex")
        domain, app_key, app_token = vtex_service.get_vtex_credentials_or_raise(
            vtex_app
        )
        api_credentials = APICredentials(
            app_key=app_key,
            app_token=app_token,
            domain=domain,
        )
        for catalog in vtex_app.vtex_catalogs.all():
            if catalog.feeds.all().exists():
                product_feed = catalog.feeds.all().first()  # The first feed created
                products = vtex_service.webhook_product_insert(
                    api_credentials, catalog, webhook_data, product_feed
                )
                if products is None:
                    logger.info(
                        f"No products to process after treatment for VTEX app {app_uuid}. Task ending."
                    )
                    return

                dict_catalog = {
                    "name": catalog.name,
                    "facebook_catalog_id": catalog.facebook_catalog_id,
                }
                flows_service.update_vtex_products(
                    products, str(catalog.app.flow_object_uuid), dict_catalog
                )
                print("Webhook Products updated and sent to flows successfully")
    except Exception as e:
        logger.error(
            f"Error on updating Webhook vtex products for app {app_uuid}, {str(e)}"
        )
