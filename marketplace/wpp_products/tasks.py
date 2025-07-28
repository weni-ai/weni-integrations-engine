import logging

import time

from datetime import datetime, timedelta

from marketplace.services.vtex.utils.enums import ProductPriority

from celery import shared_task

from django_redis import get_redis_connection
from django.db import close_old_connections
from django.core.cache import cache
from django.utils import timezone

from marketplace.clients.facebook.client import FacebookClient

from marketplace.wpp_products.models import (
    Catalog,
    ProductUploadLog,
    UploadProduct,
    WebhookLog,
)
from marketplace.clients.flows.client import FlowsClient
from marketplace.celery import app as celery_app
from marketplace.services.vtex.generic_service import (
    ProductUpdateService,
    ProductInsertionService,
    VtexServiceBase,
    ProductInsertionBySellerService,
)
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.applications.models import App

from marketplace.wpp_products.utils import (
    ProductBatchUploader,
    RedisQueue,
    SellerSyncUtils,
    UploadManager,
    ProductSyncMetaPolices,
)


logger = logging.getLogger(__name__)


SYNC_WHATSAPP_CATALOGS_LOCK_KEY = "sync-whatsapp-catalogs-lock"


@shared_task(name="sync_facebook_catalogs")
def sync_facebook_catalogs():
    project_uuids = get_projects_with_vtex_app()
    apps = App.objects.filter(code="wpp-cloud", project_uuid__in=project_uuids)
    for app in apps:
        service = FacebookCatalogSyncService(app)
        service.sync_catalogs()


def get_projects_with_vtex_app() -> list:
    apps = App.objects.filter(code="vtex")
    related_wpp_cloud_project_uuids = []
    for app in apps:
        if app.project_uuid:
            related_wpp_cloud_project_uuids.append(str(app.project_uuid))
    return related_wpp_cloud_project_uuids


class FacebookCatalogSyncService:
    SYNC_WHATSAPP_CATALOGS_LOCK_KEY = "sync-whatsapp-catalogs-lock"

    def __init__(self, app: App):
        self.app = app
        self.client = FacebookClient(app.apptype.get_system_access_token(app))
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
                active_catalog = self._get_active_catalog(wa_waba_id)

                if all_catalogs_id:
                    self._update_catalogs_on_flows(all_catalogs, active_catalog)
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

    def _get_active_catalog(self, wa_waba_id):
        try:
            response = self.client.get_connected_catalog(waba_id=wa_waba_id)
            if len(response.get("data")) > 0:
                return response.get("data")[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Error on get active catalog: {self.app.uuid} {str(e)}")
            return None

    def _update_catalogs_on_flows(self, all_catalogs, active_catalog):
        try:
            self.flows_client.update_catalogs(
                flow_object_uuid=str(self.app.flow_object_uuid),
                catalogs_data=all_catalogs,
                active_catalog=active_catalog,
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

    credentials = kwargs.get("credentials")
    catalog_uuid = kwargs.get("catalog_uuid")
    sellers = kwargs.get("sellers")
    sales_channel = kwargs.get("sales_channel")

    if not all([credentials, catalog_uuid]):
        logger.error(
            "Missing required parameters [credentials, catalog_uuid] for task_insert_vtex_products"
        )
        return

    try:
        catalog = Catalog.objects.get(uuid=catalog_uuid)
        api_credentials = APICredentials(
            app_key=credentials["app_key"],
            app_token=credentials["app_token"],
            domain=credentials["domain"],
        )
        print(f"Starting first product insert for catalog: {str(catalog.name)}")
        products = vtex_service.first_product_insert(
            api_credentials, catalog, sellers, sales_channel
        )
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

    print(
        f"finishing creation products, task: 'task_insert_vtex_products' catalog {catalog.name}"
    )
    print("=" * 40)


@celery_app.task(name="task_upload_vtex_products")
def task_upload_vtex_products(**kwargs):
    app_vtex_uuid = kwargs.get("app_vtex_uuid")
    priority = kwargs.get("priority")

    app_vtex = App.objects.get(uuid=app_vtex_uuid)
    redis_client = get_redis_connection()
    lock_key = f"upload_lock:{app_vtex_uuid}"
    lock_expiration_time = 15 * 60  # 15 minutes

    # Attempt to acquire the lock
    if redis_client.set(lock_key, "locked", nx=True, ex=lock_expiration_time):
        try:
            catalogs = app_vtex.vtex_catalogs.all()
            if not catalogs.exists():
                print("No catalogs found.")
                return

            for catalog in catalogs:
                if catalog.vtex_app:
                    logger.info(
                        f"[task_upload_vtex_products] Processing catalog: {catalog.name} for VTEX app: {app_vtex.uuid}"
                    )
                    uploader = ProductBatchUploader(catalog=catalog, priority=priority)

            uploader.process_and_upload(redis_client, lock_key, lock_expiration_time)

        finally:
            # Release the lock
            redis_client.delete(lock_key)
    else:
        print(f"Upload task for App: {app_vtex_uuid} is already in progress.")

    print(f"Processing upload for App: {app_vtex_uuid}")


@celery_app.task(name="task_cleanup_vtex_logs_and_uploads")
def task_cleanup_vtex_logs_and_uploads():
    # Delete all records from the ProductUploadLog and WebhookLog tables
    ProductUploadLog.objects.all().delete()
    WebhookLog.objects.all().delete()

    # Delete all UploadProduct records with "success" status
    UploadProduct.objects.filter(status="success").delete()

    # Update status to "pending" for all UploadProduct records with "error" status
    error_queryset = UploadProduct.objects.filter(status="error")
    if error_queryset.exists():
        error_queryset.update(status="pending")

    # Update status to "pending" for records that have been "processing" for more than 20 minutes
    time_threshold = timezone.now() - timedelta(minutes=20)
    in_processing = UploadProduct.objects.filter(
        status="processing", modified_on__lt=time_threshold
    )
    if in_processing.exists():
        in_processing.update(status="pending")

    print("Logs and successful uploads have been cleaned up.")


def send_sync(app_uuid: str, webhook: dict):
    try:
        cache_key = f"app_cache_{app_uuid}"
        app = cache.get(cache_key)
        if not app:
            app = App.objects.get(uuid=app_uuid, configured=True, code="vtex")
            cache.set(cache_key, app, timeout=300)
    except App.DoesNotExist:
        logger.info(f"No VTEX App configured with the provided UUID: {app_uuid}")
        return

    can_synchronize = app.config.get("initial_sync_completed", False)

    if not can_synchronize:
        print(f"Initial sync not completed. App:{str(app.uuid)}")
        return

    sku_id = webhook.get("IdSku")

    # Get specific sellers to sync from app config
    # This configuration is used for clients who need to synchronize only fixed set of
    # one or more specific sellers, instead of all available sellers
    sync_specific_sellers = app.config.get("sync_specific_sellers", [])

    if sync_specific_sellers:
        seller_id = _extract_sellers_ids(webhook)
        if seller_id not in sync_specific_sellers:
            print(
                f"Seller ID '{seller_id}' not in allowed list: {sync_specific_sellers}. "
                f"Webhook for App {app_uuid} ignored."
            )
            return

    if not sku_id:
        logger.info(
            f"SKU ID not provided in the request. App: {str(app.uuid)} | Webhook received: {webhook}"
        )
        return

    # Check if the app uses specific queue
    celery_queue = app.config.get("celery_queue_name", "product_synchronization")

    # Commented out on 2025-07-16 to reduce database writes
    # WebhookLog.objects.create(sku_id=sku_id, data=webhook, vtex_app=app)

    logger.info(f"App {app_uuid} uses Sync v2. Enqueuing for batch update.")

    # Extract seller_id from webhook
    seller_id = _extract_sellers_ids(webhook)
    if not seller_id:
        raise ValueError(f"Seller ID not found in webhook. App:{str(app.uuid)}")

    # Enqueue the seller and SKU in the task_enqueue_webhook
    celery_app.send_task(
        "task_enqueue_webhook",
        kwargs={"app_uuid": app_uuid, "seller": seller_id, "sku_id": sku_id},
        queue=celery_queue,
        ignore_result=True,
    )
    # Dequeue
    celery_app.send_task(
        "task_dequeue_webhooks",
        kwargs={"app_uuid": app_uuid, "celery_queue": celery_queue},
        queue=celery_queue,
        ignore_result=True,
    )


def _extract_sellers_ids(webhook: dict):
    seller_an = webhook.get("An")
    seller_chain = webhook.get("SellerChain")

    if seller_chain and seller_an:
        return seller_chain

    if seller_an and not seller_chain:
        return seller_an

    return None


@celery_app.task(name="task_insert_vtex_products_by_sellers")
def task_insert_vtex_products_by_sellers(**kwargs):
    print("Starting insertion products by seller")
    vtex_service = ProductInsertionBySellerService()

    credentials = kwargs.get("credentials")
    catalog_uuid = kwargs.get("catalog_uuid")
    sellers = kwargs.get("sellers")
    sync_all_sellers = kwargs.get("sync_all_sellers", False)
    sales_channel = kwargs.get("sales_channel")

    if not sellers and not sync_all_sellers:
        logger.error(
            "Missing required parameters [sellers or sync_all_sellers] for task_insert_vtex_products_by_sellers"
        )
        return

    if not all([credentials, catalog_uuid]):
        logger.error(
            "Missing required parameters [credentials, catalog_uuid] for task_insert_vtex_products"
        )
        return

    try:
        catalog = Catalog.objects.get(uuid=catalog_uuid)
        api_credentials = APICredentials(
            app_key=credentials["app_key"],
            app_token=credentials["app_token"],
            domain=credentials["domain"],
        )
        print(f"Starting sync by sellers for catalog: {str(catalog.name)}")

        lock_key = None
        vtex_app_uuid = str(catalog.vtex_app.uuid)
        lock_key = SellerSyncUtils.create_lock(vtex_app_uuid, sellers)

        if lock_key:
            sync_success = vtex_service.insertion_products_by_seller(
                api_credentials, catalog, sellers, sync_all_sellers, sales_channel
            )
            if not sync_success:
                print("There are no products to be shipped after processing the rules.")
                return

            # Even though the saver already triggers the upload process during batch saves,
            # this call acts as a double-check to ensure that any remaining pending tasks are started.
            UploadManager.check_and_start_upload(vtex_app_uuid)

        else:
            print(
                f"An upload is already being processed for this client: {vtex_app_uuid}"
            )

    except Exception as e:
        logger.error(
            f"An error occurred during the 'insertion_products_by_seller' for catalog {catalog.name}, {e}",
            exc_info=True,
            stack_info=True,
        )
    finally:
        if lock_key:
            print(f"Release sync-sellers lock_key: {lock_key}")
            SellerSyncUtils.release_lock(vtex_app_uuid)

    print(f"finishing 'insertion_products_by_seller'catalog {catalog.name}")
    print("=" * 40)


@celery_app.task(name="task_sync_product_policies")
def task_sync_product_policies():
    print("Starting synchronization of product policies")

    try:
        vtex_apps = App.objects.filter(code="vtex", configured=True)

        for app in vtex_apps:
            catalogs = app.vtex_catalogs.all()
            for catalog in catalogs:
                product_sync_service = ProductSyncMetaPolices(catalog)
                product_sync_service.sync_products_polices()

    except Exception as e:
        logger.exception(
            f"An error occurred during the 'task_sync_product_policies'. error: {e}"
        )
        return

    print("finishing 'task_sync_product_policies'")
    print("=" * 40)


@celery_app.task(name="task_enqueue_webhook")
def task_enqueue_webhook(app_uuid: str, seller: str, sku_id: str):
    """
    Enqueues the seller and SKU in Redis for batch processing.
    """
    try:
        queue = RedisQueue(f"webhook_queue:{app_uuid}")
        value = f"{seller}#{sku_id}"

        # Added to queue if it doesn't exist
        queue.insert(value)

        print(
            f"Webhook enqueued for App: {app_uuid}, Item: {value}, Total Enqueue: {queue.length()}"
        )
    except Exception as e:
        logger.error(f"Failed to enqueue webhook for App: {app_uuid}, {e}")


@celery_app.task(name="task_dequeue_webhooks")
def task_dequeue_webhooks(
    app_uuid: str,
    celery_queue: str,
    priority: int = ProductPriority.DEFAULT,
    batch_size: int = 5000,
):
    """
    Dequeues webhooks from Redis and dispatches them in batches.
    """
    queue_key = f"webhook_queue:{app_uuid}"
    queue = RedisQueue(queue_key)
    lock_key = f"lock:{queue_key}"
    redis = queue.redis

    lock_ttl_seconds = 60 * 5  # Lock expires in 5 minutes

    # Attempt to acquire the lock
    if not redis.set(lock_key, "locked", nx=True, ex=lock_ttl_seconds):
        logger.info(f"Task already running for App: {app_uuid}. Skipping dequeue.")
        return

    try:
        logger.info(
            f"Starting dequeue process for App: {app_uuid}. Total items: {queue.length()}"
        )

        while queue.length() > 0:
            redis.expire(lock_key, lock_ttl_seconds)  # Renew lock

            # Get batch of items
            batch = queue.get_batch(batch_size)
            if not batch:
                print(f"No items to process for App: {app_uuid}. Stopping dequeue.")
                break

            celery_app.send_task(
                "task_update_webhook_batch_products",
                kwargs={"app_uuid": app_uuid, "batch": batch, "priority": priority},
                queue=celery_queue,
                ignore_result=True,
            )
            logger.info(f"Dispatched batch of {len(batch)} items for App: {app_uuid}.")
            print(
                f"Wait for 5 seconds before the next batch processing for app : {app_uuid}"
            )
            time.sleep(5)
    except Exception as e:
        logger.error(f"Error during dequeue process for App: {app_uuid}, {e}")
    finally:
        print(
            f"Dequeue process completed for App: {app_uuid}. Removing lock key: {lock_key}"
        )
        redis.delete(lock_key)


@celery_app.task(name="task_update_webhook_batch_products")
def task_update_webhook_batch_products(
    app_uuid: str,
    batch: list,
    priority: int = ProductPriority.DEFAULT,
    sales_channel: list[str] = None,
):
    """
    Processes product updates in batches for a VTEX app.

    Priority levels:
        ProductPriority.DEFAULT: Legacy synchronization. Runs only if the app's initial sync is completed.
        ProductPriority.ON_DEMAND: On-demand sync via Celery (asynchronous).
        ProductPriority.API_ONLY: On-demand inline sync (synchronous, returns processed products).

    Args:
        app_uuid (str): UUID of the VTEX app.
        batch (list): List of seller#sku identifiers to process.
        priority (int): Type of synchronization.
            ProductPriority.DEFAULT = legacy,
            ProductPriority.ON_DEMAND = on demand,
            ProductPriority.API_ONLY = inline.
        sales_channel (list[str], optional): Sales channel identifier.

    Returns:
        If priority is ProductPriority.API_ONLY, returns the list of processed products.
        Otherwise, returns None.
    """
    start_time = datetime.now()
    vtex_base_service = VtexServiceBase()
    processed_products = None

    try:
        logger.info(f"Processing batch of {len(batch)} items for App: {app_uuid}.")

        cache_key = f"app_cache_{app_uuid}"
        vtex_app = cache.get(cache_key)
        if not vtex_app:
            vtex_app = App.objects.get(uuid=app_uuid, configured=True, code="vtex")
            cache.set(cache_key, vtex_app, timeout=300)

        # Legacy sync is allowed only if the initial sync is completed
        if priority == ProductPriority.DEFAULT and not vtex_app.config.get(
            "initial_sync_completed", False
        ):
            logger.info(f"Initial sync not completed for App: {app_uuid}. Task ending.")
            return None

        api_credentials = vtex_base_service.get_vtex_credentials_or_raise(vtex_app)
        catalog = vtex_app.vtex_catalogs.first()
        if not catalog:
            logger.info(f"No catalog found for VTEX app: {vtex_app.uuid}")
            return None

        vtex_update_service = ProductUpdateService(
            api_credentials=api_credentials,
            catalog=catalog,
            sellers_skus=batch,
            priority=priority,
            sales_channel=sales_channel,
        )

        # Receives a list of processed products from the service
        processed_products = vtex_update_service.process_batch_sync()
        if not processed_products:
            logger.info(f"Failed to process batch for App: {app_uuid}.")
            return None

    except Exception as e:
        logger.error(f"Error during batch processing for App: {app_uuid}, {e}")
        return None

    finally:
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(
            f"Finished processing batch for App: {app_uuid}. Duration: {duration:.2f} seconds."
        )

    if priority == ProductPriority.API_ONLY:
        return processed_products

    return None
