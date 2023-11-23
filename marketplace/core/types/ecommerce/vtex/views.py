from rest_framework.response import Response
from rest_framework import status

from marketplace.core.types.ecommerce.vtex.serializers import (
    VtexSerializer,
    VtexAppSerializer,
)
from marketplace.core.types import views
from marketplace.services.vtex.generic_service import VtexService
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.applications.models import App


class VtexViewSet(views.BaseAppTypeViewSet):
    serializer_class = VtexAppSerializer
    service_class = VtexService

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None

    @property
    def service(self):
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
        self.service.check_is_valid_credentials(credentials)

        try:
            # Calls the create method of the base class to create the App object
            response = super().create(request, *args, **kwargs)

            if response.status_code == status.HTTP_201_CREATED:
                app = App.objects.get(uuid=response.data["uuid"])

                updated_app = self.service.configure(app, credentials)
                return Response(data=self.get_serializer(updated_app).data)

        except Exception as e:
            app.delete()  # Remove the instance in case of exception
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return response

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
