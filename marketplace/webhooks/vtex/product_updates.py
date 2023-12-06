from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.clients.vtex.client import VtexPrivateClient
from marketplace.applications.models import App
from marketplace.services.vtex.exceptions import (
    CredentialsValidationError,
    NoVTEXAppConfiguredException,
)
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.flows.service import FlowsService


class VtexProductUpdateWebhook(APIView):
    flows_client_class = FlowsClient
    flows_service_class = FlowsService
    vtex_client_class = VtexPrivateClient
    vtex_service_class = PrivateProductsService

    def post(self, request, app_uuid):
        app = self.get_app(app_uuid)
        if not self.can_synchronize(app):
            return Response(
                {"error": "initial sync not completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        domain, app_key, app_token = self.get_credentials_or_raise(app)
        vtex_service = self.get_vtex_service(app_key, app_token)

        products_updated = vtex_service.update_product_info(domain, request.data)
        self.send_products_to_flows(products_updated)
        return Response(status=status.HTTP_200_OK)

    def get_app(self, app_uuid):
        try:
            return App.objects.get(uuid=app_uuid, configured=True, code="vtex")
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()

    def can_synchronize(self, app):
        return app.config.get("initial_sync_completed", False)

    def get_credentials_or_raise(self, app):
        domain = app.config["api_credentials"]["domain"]
        app_key = app.config["api_credentials"]["app_key"]
        app_token = app.config["api_credentials"]["app_token"]
        if not domain or not app_key or not app_token:
            raise CredentialsValidationError()
        return domain, app_key, app_token

    def get_vtex_service(self, app_key, app_token):
        client = self.vtex_client_class(app_key, app_token)
        return self.vtex_service_class(client)

    def send_products_to_flows(self, products):
        flows_service = self.flows_service_class(self.flows_client_class())
        flows_service.update_vtex_products(products)
