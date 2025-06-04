import logging

from marketplace.applications.models import App
from marketplace.wpp_products.models import ProductValidation, Catalog
from marketplace.celery import app as _celery_app

from typing import Optional, TypedDict, List

from celery import Celery

from marketplace.wpp_products.tasks import task_enqueue_webhook


logger = logging.getLogger(__name__)


class SyncOnDemandData(TypedDict):
    """
    TypedDict for holding SKU IDs and seller information for on-demand synchronization.
    """

    sku_ids: List[str]
    seller: str


class SyncOnDemandUseCase:
    """
    Use case for handling on-demand synchronization of products.

    This class manages the process of enqueuing SKU IDs for synchronization and
    dequeuing them for processing. It ensures that only valid products are enqueued
    and manages the interaction with the VTEX application and Celery tasks.
    """

    def __init__(self, celery_app: Optional[Celery] = None):
        """
        Initialize the SyncOnDemandUseCase with an optional Celery app.

        Args:
            celery_app: An optional Celery app instance. If not provided, the default
                        Celery app is used.
        """
        self.celery_app = celery_app or _celery_app

    def _get_vtex_app(self, project_uuid: str) -> App:
        """
        Retrieve the VTEX App associated with the given project UUID.

        Args:
            project_uuid: The UUID of the project to retrieve the VTEX App for.

        Returns:
            The VTEX App instance.

        Raises:
            NotFound: If no VTEX App is configured with the provided project UUID.
        """
        try:
            return App.objects.get(project_uuid=project_uuid, code="vtex")
        except App.DoesNotExist:
            logger.info(
                f"No VTEX App configured with the provided project: {project_uuid}"
            )
            return None

    def _is_product_valid(self, sku_id: str, catalog: Catalog) -> bool:
        """
        Check if a product is valid based on its SKU ID and catalog.

        Args:
            sku_id: The SKU ID of the product.
            catalog: The catalog to check the product against.

        Returns:
            True if the product is valid, False otherwise.
        """
        return ProductValidation.objects.filter(
            sku_id=sku_id, is_valid=True, catalog=catalog
        ).exists()

    def _product_exists(self, sku_id: str, catalog: Catalog) -> bool:
        """
        Check if a product exists based on its SKU ID and catalog.

        Args:
            sku_id: The SKU ID of the product.
            catalog: The catalog to check the product against.

        Returns:
            True if the product exists, False otherwise.
        """
        return ProductValidation.objects.filter(sku_id=sku_id, catalog=catalog).exists()

    def _enqueue_skus(self, app_uuid: str, seller: str, sku_id: str):
        """
        Enqueue SKU IDs for processing in a Redis queue.

        This method adds SKU IDs to a Redis queue for processing. The queue is populated
        by various means and consumed by the dequeue process for further handling and
        uploading results to Meta.

        Args:
            app_uuid: The UUID of the application.
            seller: The seller associated with the SKU.
            sku_id: The SKU ID to enqueue.
        """
        logger.info(f"Enqueuing sku {sku_id} for seller {seller}")
        task_enqueue_webhook(app_uuid, seller, sku_id)

    def _dequeue_skus(self, app_uuid: str, celery_queue: str):
        """
        Dequeue SKU IDs for processing.

        This method sends a task to dequeue SKU IDs from the Redis queue for processing.

        Args:
            app_uuid: The UUID of the application.
            celery_queue: The name of the Celery queue to use.
        """
        self.celery_app.send_task(
            "task_dequeue_webhooks",
            kwargs={"app_uuid": app_uuid, "celery_queue": celery_queue, "priority": 1},
            queue=celery_queue,
            ignore_result=True,
        )

    def execute(self, data: SyncOnDemandData, project_uuid: str) -> None:
        """
        Execute the on-demand synchronization process.

        This method processes the provided SKU IDs, enqueues valid ones, and
        initiates the dequeue process.

        Args:
            data: The SyncOnDemandData containing SKU IDs and seller information.
            project_uuid: The UUID of the project to synchronize.
        """
        seller = data.get("seller")
        sku_ids = set(data.get("sku_ids"))
        vtex_app = self._get_vtex_app(project_uuid)
        catalog = vtex_app.vtex_catalogs.first()
        celery_queue = "vtex-sync-on-demand"

        if not vtex_app:
            return

        app_uuid = str(vtex_app.uuid)

        invalid_skus = set()

        for sku_id in sku_ids:
            if self._product_exists(sku_id, catalog) and not self._is_product_valid(
                sku_id, catalog
            ):
                invalid_skus.add(sku_id)

        valid_skus = sku_ids - invalid_skus

        for sku_id in valid_skus:
            self._enqueue_skus(app_uuid, seller, sku_id, celery_queue)

        self._dequeue_skus(app_uuid, celery_queue)
