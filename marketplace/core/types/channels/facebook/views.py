from django.conf import settings

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from marketplace.clients.facebook.client import FacebookClient
from marketplace.connect.client import ConnectProjectClient
from marketplace.core.types.channels.facebook.usecases.search_products import (
    FacebookSearchProductsUseCase,
)
from marketplace.services.facebook.service import FacebookService
from marketplace.utils.aws.lambda_validation import LambdaURLValidator

from .serializers import (
    FacebookSearchProductsSerializer,
    FacebookSerializer,
    FacebookConfigureSerializer,
)
from marketplace.core.types import views
from . import type as type_


class FacebookViewSet(views.BaseAppTypeViewSet):
    serializer_class = FacebookSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.FacebookType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.FacebookType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()
        self.serializer_class = FacebookConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        if app.flow_object_uuid is None:
            validated_config = serializer.validated_data.get("config")
            payload = {
                "user_access_token": validated_config.get("user_access_token"),
                "fb_user_id": validated_config.get("fb_user_id"),
                "page_name": validated_config.get("page_name"),
                "page_id": validated_config.get("page_id"),
            }

            user = request.user
            client = ConnectProjectClient()

            response = client.create_channel(
                user.email, app.project_uuid, payload, app.flows_type_code
            )

            flows_config = response.get("config")
            app.flow_object_uuid = response.get("uuid")
            app.configured = True
            app.config["title"] = response.get("name")
            app.config["address"] = response.get("address")
            app.config["page_name"] = flows_config.get("page_name")
            app.save()

        return Response(serializer.data)


class FacebookSearchProductsView(APIView, LambdaURLValidator):  # pragma: no cover
    authentication_classes = []
    facebook_client = FacebookClient(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

    @property
    def _use_case(self):
        """Lazily create (and cache) the use-case only when needed."""
        if not hasattr(self, "__use_case"):
            facebook_client = FacebookClient(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)
            service = FacebookService(facebook_client)
            self.__use_case = FacebookSearchProductsUseCase(service)
        return self.__use_case

    def post(self, request, *args, **kwargs):
        validation_response = self._validate_lambda_url(request)

        if validation_response:
            return validation_response
        serializer = FacebookSearchProductsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = self._use_case.execute(
            catalog_id=serializer.validated_data["catalog_id"],
            product_ids=serializer.validated_data["product_ids"],
            fields=serializer.validated_data.get("fields"),
            summary=serializer.validated_data.get("summary"),
            limit=serializer.validated_data.get("limit"),
        )
        return Response(result, status=status.HTTP_200_OK)

    def _validate_lambda_url(self, request):
        validation_response = self.protected_resource(request)
        if validation_response.status_code != 200:
            return validation_response
        return None
