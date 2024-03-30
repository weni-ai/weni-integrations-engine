import logging

from datetime import datetime

from celery import shared_task

from django.db import reset_queries, close_old_connections

from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.webhook.vtex.webhook_manager import WebhookQueueManager
from marketplace.wpp_products.models import Catalog
from marketplace.clients.flows.client import FlowsClient
from marketplace.celery import app as celery_app
from marketplace.services.vtex.generic_service import (
    ProductUpdateService,
    ProductInsertionService,
    VtexServiceBase,
)
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.services.flows.service import FlowsService
from marketplace.core.types import APPTYPES
from marketplace.applications.models import App

from django_redis import get_redis_connection
from django.core.cache import cache


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
            logger.error(
                f"Error on list all catalogs for App: {self.app.uuid} {str(e)}"
            )
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
    print("Starting task: 'task_insert_vtex_products'")
    vtex_service = ProductInsertionService()
    flows_service = FlowsService(FlowsClient())

    credentials = kwargs.get("credentials")
    catalog_uuid = kwargs.get("catalog_uuid")

    if not all([credentials, catalog_uuid]):
        logger.error(
            "Missing required parameters [credentials, catalog_uuid] for task_insert_vtex_products"
        )
        return

    try:
        # Reset queries and close old connections for a clean state and performance.
        # Prevents memory leak from stored queries and unstable database connections
        # before further operations.
        reset_queries()
        close_old_connections()

        catalog = Catalog.objects.get(uuid=catalog_uuid)
        api_credentials = APICredentials(
            app_key=credentials["app_key"],
            app_token=credentials["app_token"],
            domain=credentials["domain"],
        )
        print(f"Starting first product insert for catalog: {str(catalog.name)}")
        products = vtex_service.first_product_insert(api_credentials, catalog)
        if products is None:
            print("There are no products to be shipped after processing the rules")
            return

    except Exception as e:
        logger.exception(
            f"An error occurred during the first insertion of vtex products for catalog {catalog.name}, {e}"
        )
        return
    finally:
        close_old_connections()

    try:
        dict_catalog = {
            "name": catalog.name,
            "facebook_catalog_id": catalog.facebook_catalog_id,
        }
        flows_service.update_vtex_products(
            products, str(catalog.app.flow_object_uuid), dict_catalog
        )
        print("Products successfully sent to flows")
    except Exception as e:
        logger.error(
            f"Error on send vtex products to flows for catalog {catalog_uuid}, {e}"
        )

    print(
        f"finishing creation products, task: 'task_insert_vtex_products' catalog {catalog.name}"
    )
    print("=" * 40)


@celery_app.task(name="task_update_vtex_products")
def task_update_vtex_products(**kwargs):
    print("Starting task: 'task_update_vtex_products'")
    vtex_base_service = VtexServiceBase()
    # flows_service = FlowsService(FlowsClient())

    app_uuid = kwargs.get("app_uuid")

    queue_manager = WebhookQueueManager(app_uuid)
    redis = get_redis_connection()
    lock_key = queue_manager.get_lock_key()

    lock = redis.lock(lock_key, timeout=7200)
    if lock.acquire(blocking=False):
        processing_key = queue_manager.get_sku_list_key()
        webhooks_in_processing = cache.get(processing_key, {})
        try:
            while webhooks_in_processing:
                close_old_connections()

                skus_ids = queue_manager.dequeue_webhook_data()
                if skus_ids is None:
                    break

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                print(
                    f"Processing product update for App UUID: {app_uuid}, SKU IDs: {skus_ids} at {current_time}"
                )
                vtex_app = App.objects.get(uuid=app_uuid, configured=True, code="vtex")
                (
                    domain,
                    app_key,
                    app_token,
                ) = vtex_base_service.get_vtex_credentials_or_raise(vtex_app)
                api_credentials = APICredentials(
                    app_key=app_key, app_token=app_token, domain=domain
                )

                catalog = vtex_app.vtex_catalogs.first()
                if not catalog or not catalog.feeds.first():
                    logger.error(
                        f"No data feed found in the database. Vtex app: {vtex_app.uuid}"
                    )
                    continue

                product_feed = catalog.feeds.first()
                print(f"Starting product update for app: {str(vtex_app.uuid)}")

                vtex_update_service = ProductUpdateService(
                    api_credentials, catalog, skus_ids, product_feed
                )
                products = vtex_update_service.webhook_product_insert()
                if products is None:
                    print(
                        f"No products to process after treatment for VTEX app {app_uuid}. Task ending."
                    )
                    continue

                # Temporarily removes the sending of products to flows [03-30-2024]

                # dict_catalog = {
                #     "name": catalog.name,
                #     "facebook_catalog_id": catalog.facebook_catalog_id,
                # }

                # try:
                #     flows_service.update_vtex_products(
                #         products, str(catalog.app.flow_object_uuid), dict_catalog
                #     )
                #     print("Products successfully sent to flows")
                # except Exception as e:
                #     logger.error(f"Failed to send products to flows: {str(e)}")

                # Reloads in-process webhooks to check for new items after current processing
                webhooks_in_processing = cache.get(processing_key, [])

        except Exception as e:
            logger.error(
                f"An error occurred during the updating Webhook vtex products for app {app_uuid}, {str(e)}"
            )

        finally:
            lock.release()
    else:
        print("Unable to acquire lock, another process is running.")

    print("Finishing update vtex product")
    print("=" * 40)
