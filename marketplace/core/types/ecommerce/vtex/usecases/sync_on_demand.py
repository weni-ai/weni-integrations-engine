from rest_framework.exceptions import NotFound

from marketplace.applications.models import App
from marketplace.wpp_products.models import ProductValidation, Catalog
from marketplace.celery import app as _celery_app

from typing import Optional, TypedDict, List

from celery import Celery


class SyncOnDemandData(TypedDict):
    sku_ids: List[str]
    seller: str


class SyncOnDemandUseCase:
    def __init__(self, celery_app: Optional[Celery] = None):
        self.celery_app = celery_app or _celery_app

    def _get_vtex_app(self, project_uuid: str) -> App:
        try:
            return App.objects.get(project_uuid=project_uuid, code="vtex")
        except App.DoesNotExist:
            raise NotFound(
                f"No VTEX App configured with the provided project: {project_uuid}"
            )

    def _is_product_valid(self, sku_id: str, catalog: Catalog) -> bool:
        return ProductValidation.objects.filter(
            sku_id=sku_id, is_valid=True, catalog=catalog
        ).exists()

    def _product_exists(self, sku_id: str, catalog: Catalog) -> bool:
        return ProductValidation.objects.filter(sku_id=sku_id, catalog=catalog).exists()

    def _trigger_tasks(
        self, app_uuid: str, seller: str, sku_id: str, celery_queue: str
    ):
        self.celery_app.send_task(
            "task_enqueue_webhook",
            kwargs={"app_uuid": app_uuid, "seller": seller, "sku_id": sku_id},
            queue=celery_queue,
            ignore_result=True,
        )
        self.celery_app.send_task(
            "task_dequeue_webhooks",
            kwargs={"app_uuid": app_uuid, "celery_queue": celery_queue},
            queue=celery_queue,
            ignore_result=True,
        )

    def execute(self, data: SyncOnDemandData, project_uuid: str) -> None:
        seller = data.get("seller")
        sku_ids = set(data.get("sku_ids"))
        vtex_app = self._get_vtex_app(project_uuid)
        catalog = vtex_app.vtex_catalogs.first()
        celery_queue = vtex_app.config.get(
            "celery_queue_name", "product_synchronization"
        )

        app_uuid = str(vtex_app.uuid)

        invalid_skus = set()

        for sku_id in sku_ids:
            if self._product_exists(sku_id, catalog) and not self._is_product_valid(
                sku_id, catalog
            ):
                invalid_skus.add(sku_id)

        valid_skus = sku_ids - invalid_skus

        for sku_id in valid_skus:
            self._trigger_tasks(app_uuid, seller, sku_id, celery_queue)
