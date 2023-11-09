from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from marketplace.core.types.externals.vtex.serializers import VtexDomainSerializer
from marketplace.core.types.externals.vtex.serializers import VtexSerializer
from marketplace.core.types import views
from marketplace.clients.vtex.client import VtexPublicClient
from marketplace.services.vtex.public.products.products_vtex_service import (
    VtexProductsService,
)


class VtexViewSet(views.BaseAppTypeViewSet):
    serializer_class = VtexSerializer

    service_class = VtexProductsService
    client_class = VtexPublicClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None

    @property
    def service(self):  # pragma: no cover
        if not self._service:
            self._service = self.service_class(self.client_class())
        return self._service

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, *args, **kwargs):
        app_instance = self.get_object()
        serializer = VtexDomainSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            domain = serializer.validated_data["domain"]
            try:
                updated_app = self.service.configure(app_instance, domain)
                return Response(data=self.get_serializer(updated_app).data)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
