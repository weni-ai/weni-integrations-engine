import logging

from marketplace.applications.models import App
from marketplace.wpp_products.models import ProductValidation, Catalog
from marketplace.celery import app as _celery_app

from typing import Optional, TypedDict, List

from celery import Celery


logger = logging.getLogger(__name__)


class SyncOnDemandData(TypedDict):
    """
    TypedDict for holding SKU IDs and seller information for on-demand synchronization.
    """

    sku_ids: List[str]
    seller: str
    salles_channel: Optional[str]


class SyncOnDemandUseCase:
    """
    Use case for handling on-demand synchronization of products.

    This class manages the process of enqueuing SKU IDs for synchronization and
    dispatching them for processing. It ensures that only valid products are enqueued
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

    def _get_vtex_app(self, project_uuid: str) -> Optional[App]:
        """
        Retrieve the VTEX App associated with the given project UUID.

        Args:
            project_uuid: The UUID of the project to retrieve the VTEX App for.

        Returns:
            The VTEX App instance or None if not found.
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

    def _build_batch(self, seller: str, sku_ids: List[str]) -> List[str]:
        """
        Build a batch of SKU IDs prefixed with the seller information.

        Args:
            seller: The seller's identifier.
            sku_ids: List of SKU IDs to be processed.

        Returns:
            A list of strings combining seller and SKU IDs.
        """
        return [f"{seller}#{sku_id}" for sku_id in sku_ids]

    def _dispatch_skus(
        self,
        app_uuid: str,
        celery_queue: str,
        skus_batch: List[str],
        salles_channel: Optional[str] = None,
    ) -> None:
        """
        Dispatch SKU IDs for processing by sending a task to Celery.

        Args:
            app_uuid: The UUID of the application.
            celery_queue: The name of the Celery queue to use.
            skus_batch: The batch of SKU IDs to process.
        """

        if salles_channel:
            kwargs = {
                "app_uuid": app_uuid,
                "batch": skus_batch,
                "priority": 1,
                "salles_channel": salles_channel,
            }
        else:
            kwargs = {"app_uuid": app_uuid, "batch": skus_batch, "priority": 1}

        logger.info(
            f"Dispatching skus: {skus_batch} to {celery_queue} - sync on demand"
        )
        self.celery_app.send_task(
            "task_update_webhook_batch_products",
            kwargs=kwargs,
            queue=celery_queue,
            ignore_result=True,
        )

    def execute(self, data: SyncOnDemandData, project_uuid: str) -> None:
        """
        Execute the on-demand synchronization process.

        This method processes the provided SKU IDs, enqueues valid ones, and
        initiates the dispatch process.

        Args:
            data: The SyncOnDemandData containing SKU IDs and seller information.
            project_uuid: The UUID of the project to synchronize.
        """
        seller = data.get("seller")
        sku_ids = set(data.get("sku_ids"))
        salles_channel = data.get("salles_channel")
        vtex_app = self._get_vtex_app(project_uuid)

        if not vtex_app:
            return

        catalog = vtex_app.vtex_catalogs.first()
        celery_queue = "vtex-sync-on-demand"
        app_uuid = str(vtex_app.uuid)

        invalid_skus = set()

        for sku_id in sku_ids:
            if self._product_exists(sku_id, catalog) and not self._is_product_valid(
                sku_id, catalog
            ):
                invalid_skus.add(sku_id)

        valid_skus = sku_ids - invalid_skus

        skus_batch = self._build_batch(seller, valid_skus)

        self._dispatch_skus(app_uuid, celery_queue, skus_batch, salles_channel)
