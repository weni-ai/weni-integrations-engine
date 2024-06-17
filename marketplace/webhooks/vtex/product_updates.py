from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from marketplace.wpp_products.tasks import send_sync


class VtexProductUpdateWebhook(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, app_uuid):
        send_sync(app_uuid=str(app_uuid), webhook=request.data)
        return Response(status=status.HTTP_200_OK)
