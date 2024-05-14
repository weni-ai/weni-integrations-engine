import requests

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from django.core.exceptions import ObjectDoesNotExist

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

    def get_queue_manager(self, app_uuid) -> WebhookQueueManager:  # pragma: no cover
        return self.queue_manager_class(app_uuid)

    def get_app(self, app_uuid):
        try:
            return App.objects.get(uuid=app_uuid, configured=True, code="vtex")
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()

    def can_synchronize(self, app):
        return app.config.get("initial_sync_completed", False)

    def to_staging(self, app):
        return app.config.get("redirects_to_staging", False)

    def get_sku_id(self, request):
        sku_id = request.data.get("IdSku")
        if not sku_id:
            raise ValueError("SKU ID not provided in the request")
        return sku_id

    def post(self, request, app_uuid):
        try:
            app = self.get_app(app_uuid)
            if not self.can_synchronize(app):
                return Response(
                    {"error": "Initial sync not completed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # TODO: Remove redirect
            if self.to_staging(app):
                staging_url = "https://integrations-engine.stg.cloud.weni.ai"
                url = f"{staging_url}/api/v1/webhook/vtex/{app_uuid}/products-update/api/notification/"
                requests.post(url=url, data=request.data)
                return Response({"message": "Redirected"}, status=status.HTTP_200_OK)

            sku_id = self.get_sku_id(request)
            queue_manager = self.get_queue_manager(str(app_uuid))

            queue_manager.enqueue_webhook_data(sku_id, request.data)

            if not queue_manager.is_processing_locked():
                celery_app.send_task(
                    "task_update_vtex_products",
                    kwargs={"app_uuid": str(app_uuid)},
                    queue="product_synchronization",
                )
                message = "Webhook product update process started"
            else:
                message = "Webhook product update added to the processing queue"

            return Response({"message": message}, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response(
                {"error": "App not found"}, status=status.HTTP_404_NOT_FOUND
            )
