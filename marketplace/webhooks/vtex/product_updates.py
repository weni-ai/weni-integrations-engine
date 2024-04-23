from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.celery import app as celery_app


class VtexProductUpdateWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, app_uuid, seller_id=None):
        celery_app.send_task(
            "task_send_vtex_webhook",
            kwargs={
                "app_uuid": str(app_uuid),
                "seller_id": seller_id,
                "webhook": request.data,
            },
            queue="product_synchronization",
        )
        if seller_id:
            message = "Product update by seller was called"
        else:
            message = "Product update was called"

        return Response({"message": message}, status=status.HTTP_200_OK)
