from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.applications.models import App
from marketplace.services.vtex.exceptions import (
    NoVTEXAppConfiguredException,
)
from marketplace.services.webhook.vtex.webhook_manager import WebhookQueueManager
from marketplace.celery import app as celery_app


class VtexProductUpdateWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    queue_manager_class = WebhookQueueManager

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._queue_manager = None

    def get_queue_manager(
        self, app_uuid, sku_id
    ) -> WebhookQueueManager:  # pragma: no cover
        return self.queue_manager_class(app_uuid, sku_id)

    def post(self, request, app_uuid):
        app = self.get_app(app_uuid)
        if not self.can_synchronize(app):
            return Response(
                {"error": "Initial sync not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sku_id = self.get_sku_id()
        queue_manager = self.get_queue_manager(app_uuid, sku_id)
        if queue_manager.have_processing_product():
            queue_manager.enqueue_webhook_data(request.data)
            return Response(
                {"message": "Webhook product update added to the processing queue"},
                status=status.HTTP_200_OK,
            )

        celery_app.send_task(
            "task_update_vtex_products",
            kwargs={
                "app_uuid": app_uuid,
                "sku_id": sku_id,
                "webhook_data": request.data,
            },
            queue="product_synchronization",
        )

        return Response(
            {"message": "Webhook product update process started"},
            status=status.HTTP_200_OK,
        )

    def get_app(self, app_uuid):
        try:
            return App.objects.get(uuid=app_uuid, configured=True, code="vtex")
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()

    def can_synchronize(self, app):
        return app.config.get("initial_sync_completed", False)

    def get_sku_id(self):
        sku_id = self.request.data.get("IdSku")
        if not sku_id:
            return Response(
                {"error": "SKU ID not provided in the request"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return sku_id
