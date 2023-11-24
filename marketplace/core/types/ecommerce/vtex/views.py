from rest_framework.response import Response
from rest_framework import status

from marketplace.core.types.ecommerce.vtex.serializers import (
    VtexSerializer,
    VtexAppSerializer,
)
from marketplace.core.types import views
from marketplace.services.vtex.generic_service import VtexService
from marketplace.services.vtex.generic_service import APICredentials


class VtexViewSet(views.BaseAppTypeViewSet):
    serializer_class = VtexAppSerializer
    service_class = VtexService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None

    @property
    def service(self):  # pragma: no cover
        if not self._service:
            self._service = self.service_class()

        return self._service

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    def create(self, request, *args, **kwargs):
        serializer = VtexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        # Validate before starting creation
        credentials = APICredentials(
            app_key=validated_data.get("app_key"),
            app_token=validated_data.get("app_token"),
            domain=validated_data.get("domain"),
        )
        wpp_cloud_uuid = validated_data["wpp_cloud_uuid"]
        self.service.check_is_valid_credentials(credentials)
        # Calls the create method of the base class to create the App object
        super().create(request, *args, **kwargs)
        app = self.get_app()
        try:
            updated_app = self.service.configure(app, credentials, wpp_cloud_uuid)
            return Response(
                data=self.get_serializer(updated_app).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            app.delete()  # if there are exceptions, remove the created instance
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
