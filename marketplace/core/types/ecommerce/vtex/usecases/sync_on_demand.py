from django.core.cache import cache

from rest_framework.exceptions import NotFound, ValidationError

from marketplace.applications.models import App
from marketplace.wpp_products.models import ProductValidation, Catalog
from marketplace.celery import app as _celery_app

from typing import Optional, TypedDict

from celery import Celery

CACHE_KEY = "app_cache_{app_uuid}"


class SyncOnDemandData(TypedDict):
    id_sku: str
    seller_an: str
    seller_chain: str


class SyncOnDemandUseCase:
    def __init__(self, celery_app: Optional[Celery] = None):
        self.celery_app = celery_app or _celery_app

    def _get_cache_key(self, app_uuid: str) -> str:
        return CACHE_KEY.format(app_uuid)

    def _get_app_from_cache(self, app_uuid: str) -> Optional[App]:
        cache_key = self._get_cache_key(app_uuid)
        app = cache.get(cache_key)
        return app

    def _get_app_from_db(self, app_uuid: str) -> App:
        try:
            app = App.objects.get(uuid=app_uuid, configured=True, code="vtex")
            return app
        except App.DoesNotExist:
            return NotFound(
                f"No VTEX App configured with the provided UUID: {app_uuid}"
            )

    def _set_app_in_cache(self, app: App):
        cache_key = self._get_cache_key(str(app.uuid))
        cache.set(cache_key, app, timeout=300)

    def _get_app(self, app_uuid: str) -> App:
        app = self._get_app_from_cache(app_uuid)

        if app is None:
            app = self._get_app_from_db(app_uuid)
            self._set_app_in_cache(app)

        return app

    def _get_seller(self, data: SyncOnDemandData) -> str:
        seller_an = data.get("seller_an")
        seller_chain = data.get("seller_chain")

        return seller_an or seller_chain

    def _is_product_valid(self, sku_id: str, catalog: Catalog) -> None:
        return ProductValidation.objects.filter(
            sku_id=sku_id, is_valid=True, catalog=catalog
        ).exists()

    def _trigger_tasks(
        self, app_uuid: str, seller_id: str, sku_id: str, celery_queue: str
    ):
        self.celery_app.send_task(
            "task_enqueue_webhook",
            kwargs={"app_uuid": app_uuid, "seller": seller_id, "sku_id": sku_id},
            queue=celery_queue,
            ignore_result=True,
        )
        self.celery_app.send_task(
            "task_dequeue_webhooks",
            kwargs={"app_uuid": app_uuid, "celery_queue": celery_queue},
            queue=celery_queue,
            ignore_result=True,
        )

    def execute(self, data: SyncOnDemandData, app_uuid: str) -> None:
        seller_id = self._get_seller(data)
        sku_id = data.get("sku_id")
        vtex_app = self._get_app(app_uuid)

        if seller_id is None:
            raise ValidationError("Seller ID not found in request.")

        catalog = vtex_app.vtex_catalogs.first()

        if not self._is_product_valid(sku_id, catalog):
            raise ValidationError(f"Informed product is not valid: {sku_id}")

        celery_queue = vtex_app.config.get(
            "celery_queue_name", "product_synchronization"
        )

        self._trigger_tasks(app_uuid, seller_id, sku_id, celery_queue)
