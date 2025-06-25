from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.celery import app as celery_app


class FacebookWebhook(APIView):  # pragma: no cover
    authentication_classes = []
    permission_classes = [AllowAny]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def post(self, request):
        celery_app.send_task(
            name="update_templates_by_webhook",
            kwargs={"webhook_data": request.data},
        )

        # Also send the task to update account status since multiple entries can exist in a single webhook
        celery_app.send_task(
            name="update_account_info_by_webhook",
            kwargs={"webhook_data": request.data},
        )

        return Response(status=status.HTTP_200_OK)
