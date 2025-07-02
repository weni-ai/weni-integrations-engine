import logging

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, TypedDict

from marketplace.applications.models import App
from marketplace.core.types.ecommerce.dtos.sync_on_demand_dto import SyncOnDemandDTO
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.wpp_products.models import ProductValidation, Catalog


logger = logging.getLogger(__name__)


class SyncData(TypedDict):
    """
    Payload for product-sync operations.
    """

    sku_ids: List[str]
    seller: str
    salles_channel: Optional[str]


class BaseSyncUseCase(ABC):
    """
    Abstract base for all product-sync use cases.
    """

    def __init__(self, *, priority: int) -> None:
        """
        Args:
            priority: Task priority level.
        """
        self.priority = priority

    def _get_vtex_app(self, project_uuid: str) -> Optional[App]:
        """
        Fetch the VTEX app for a given project UUID.
        """
        try:
            return App.objects.get(project_uuid=project_uuid, code="vtex")
        except App.DoesNotExist:
            logger.info(f"No VTEX App configured with project: {project_uuid}")
            return None

    def _is_product_valid(self, sku_id: str, catalog: Catalog) -> bool:
        """
        Verify if a specific SKU is marked as valid.
        """
        return ProductValidation.objects.filter(
            sku_id=sku_id,
            catalog=catalog,
            is_valid=True,
        ).exists()

    def _product_exists(self, sku_id: str, catalog: Catalog) -> bool:
        """
        Check if the product is present in the catalog (regardless of validity).
        """
        return ProductValidation.objects.filter(
            sku_id=sku_id,
            catalog=catalog,
        ).exists()

    @staticmethod
    def _build_batch(seller: str, sku_ids: List[str]) -> List[str]:
        """
        Concatenate seller and SKU IDs using the expected format.
        """
        return [f"{seller}#{sku_id}" for sku_id in sku_ids]

    def execute(
        self, dto: SyncOnDemandDTO, project_uuid: str
    ) -> List[FacebookProductDTO]:
        """
        Validate SKUs and delegate the dispatch strategy to subclasses.

        Returns:
            Whatever the concrete implementation of `_dispatch_skus` returns.
        """
        seller: str = dto.seller
        sku_ids: Set[str] = set(dto.sku_ids)
        salles_channel: Optional[str] = dto.salles_channel

        vtex_app = self._get_vtex_app(project_uuid)
        if not vtex_app:
            return None

        catalog = vtex_app.vtex_catalogs.first()
        app_uuid = str(vtex_app.uuid)
        celery_queue = "vtex-sync-on-demand"

        invalid_skus = {
            sku_id
            for sku_id in sku_ids
            if self._product_exists(sku_id, catalog)
            and not self._is_product_valid(sku_id, catalog)
        }

        valid_skus = sku_ids - invalid_skus
        skus_batch = self._build_batch(seller, list(valid_skus))

        return self._dispatch_skus(
            app_uuid=app_uuid,
            celery_queue=celery_queue,
            skus_batch=skus_batch,
            salles_channel=salles_channel,
            invalid_skus=invalid_skus,
        )

    @abstractmethod
    def _dispatch_skus(
        self,
        *,
        app_uuid: str,
        celery_queue: str,
        skus_batch: List[str],
        salles_channel: Optional[str],
        invalid_skus: Set[str],
    ) -> Any:
        """
        Dispatch the SKUs according to the use case's delivery strategy.
        """
        ...
