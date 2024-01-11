from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.applications.models import App
from marketplace.services.vtex.exceptions import (
    NoVTEXAppConfiguredException,
)
from marketplace.celery import app as celery_app


class VtexProductUpdateWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def post(self, request, app_uuid):
        app = self.get_app(app_uuid)
        if not self.can_synchronize(app):
            return Response(
                {"error": "initial sync not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        celery_app.send_task(
            name="task_update_vtex_products",
            kwargs={"webhook_data": request.data, "app_uuid": app_uuid},
        )
        return Response(status=status.HTTP_200_OK)

    def get_app(self, app_uuid):
        try:
            return App.objects.get(uuid=app_uuid, configured=True, code="vtex")
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()

    def can_synchronize(self, app):
        return app.config.get("initial_sync_completed", False)
