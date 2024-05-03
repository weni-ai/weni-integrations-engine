from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.celery import app as celery_app


class VtexProductUpdateWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, app_uuid):
        celery_app.send_task(
            "task_forward_vtex_webhook",
            kwargs={
                "app_uuid": str(app_uuid),
                "webhook": request.data,
            },
            queue="product_synchronization",
        )

        return Response(status=status.HTTP_200_OK)
