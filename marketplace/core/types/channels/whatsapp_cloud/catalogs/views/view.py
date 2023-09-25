from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.core.types.channels.whatsapp_cloud.services.facebook import (
    FacebookService,
)
from marketplace.wpp_products.models import Catalog
from marketplace.applications.models import App
from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.serializers import (
    CatalogSerializer,
    ToggleVisibilitySerializer,
)


class CatalogBaseViewSet(viewsets.ViewSet):
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fb_service = None

    @property
    def fb_service(self):  # pragma: no cover
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class())
        return self._fb_service

    def _get_catalog(self, catalog_uuid, app_uuid):
        return get_object_or_404(
            Catalog, uuid=catalog_uuid, app__uuid=app_uuid, app__code="wpp-cloud"
        )


class CatalogViewSet(CatalogBaseViewSet):
    serializer_class = CatalogSerializer

    def retrieve(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = self._get_catalog(catalog_uuid, app_uuid)

        connected_catalog_id = self.fb_service.get_connected_catalog(catalog.app)

        serialized_data = self.serializer_class(catalog).data
        serialized_data["is_connected"] = (
            catalog.facebook_catalog_id == connected_catalog_id
        )
        return Response(serialized_data)

    def list(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        catalogs = Catalog.objects.filter(app__uuid=app_uuid, app=app)
        connected_catalog_id = self.fb_service.get_connected_catalog(app)

        catalog_data = []
        for catalog in catalogs:
            serialized_data = self.serializer_class(catalog).data
            serialized_data["is_connected"] = (
                catalog.facebook_catalog_id == connected_catalog_id
            )
            catalog_data.append(serialized_data)

        return Response(catalog_data)

    @action(detail=True, methods=["POST"])
    def enable_catalog(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = self._get_catalog(catalog_uuid, app_uuid)
        response = self.fb_service.enable_catalog(catalog)
        return Response(response)

    @action(detail=True, methods=["POST"])
    def disable_catalog(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = self._get_catalog(catalog_uuid, app_uuid)
        response = self.fb_service.disable_catalog(catalog)
        return Response(response)


class CommerceSettingsViewSet(CatalogBaseViewSet):
    serializer_class = ToggleVisibilitySerializer

    @action(detail=False, methods=["GET"])
    def commerce_settings_status(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        response = self.fb_service.wpp_commerce_settings(app)
        return Response(response)

    @action(detail=False, methods=["POST"])
    def toggle_catalog_visibility(self, request, app_uuid, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        enable_visibility = serializer.validated_data["enable"]

        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        response = self.fb_service.toggle_catalog_visibility(app, enable_visibility)
        return Response(response)

    @action(detail=False, methods=["POST"])
    def toggle_cart_visibility(self, request, app_uuid, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        enable_cart = serializer.validated_data["enable"]

        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        response = self.fb_service.toggle_cart(app, enable_cart)
        return Response(response)

    @action(detail=False, methods=["GET"])
    def get_active_catalog(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        response = self.fb_service.get_connected_catalog(app)
        return Response(response)
