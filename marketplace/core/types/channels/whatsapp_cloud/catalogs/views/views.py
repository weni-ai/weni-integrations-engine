from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.core.types.channels.whatsapp_cloud.services.flows import (
    FlowsService,
)
from marketplace.wpp_products.models import Catalog
from marketplace.applications.models import App

from marketplace.clients.facebook.client import FacebookClient
from marketplace.clients.flows.client import FlowsClient

from marketplace.wpp_products.serializers import (
    CatalogSerializer,
    ProductSerializer,
    ToggleVisibilitySerializer,
    TresholdSerializer,
    CatalogListSerializer,
)
from marketplace.services.vtex.generic_service import VtexServiceBase
from marketplace.celery import app as celery_app


class BaseViewSet(viewsets.ModelViewSet):
    fb_service_class = FacebookService
    flows_service_class = FlowsService

    fb_client_class = FacebookClient
    flows_client_class = FlowsClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fb_service = None
        self._flows_service = None

    def fb_service(self, app: App):  # pragma: no cover
        access_token = app.apptype.get_access_token(app)
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class(access_token))
        return self._fb_service

    @property
    def flows_service(self):  # pragma: no cover
        if not self._flows_service:
            self._flows_service = self.flows_service_class(self.flows_client_class())
        return self._flows_service


class Pagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 500


class CatalogViewSet(BaseViewSet):
    serializer_class = CatalogSerializer
    pagination_class = Pagination
    vtex_base_class = VtexServiceBase

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._vtex_app_service = None

    @property
    def vtex_service(self):  # pragma: no cover
        if not self._vtex_app_service:
            self._vtex_app_service = self.vtex_base_class()
        return self._vtex_app_service

    def filter_queryset(self, queryset):
        params = self.request.query_params
        name = params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)

        return queryset

    def get_queryset(self):
        app_uuid = self.kwargs.get("app_uuid")
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        return Catalog.objects.filter(app=app).order_by("name")

    def get_object(self):
        queryset = self.get_queryset()
        catalog_uuid = self.kwargs.get("catalog_uuid")
        return get_object_or_404(queryset, uuid=catalog_uuid)

    def _get_catalog(self, catalog_uuid, app_uuid):
        return get_object_or_404(
            Catalog, uuid=catalog_uuid, app__uuid=app_uuid, app__code="wpp-cloud"
        )

    def create(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        vtex_app = self.vtex_service.app_manager.get_vtex_app_or_error(app.project_uuid)
        service = self.fb_service(app)
        catalog, _fba_catalog_id = service.create_vtex_catalog(
            serializer.validated_data, app, vtex_app, self.request.user
        )
        if not catalog:
            return Response(
                {"detail": "Failed to create catalog on Facebook."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        credentials = {
            "app_key": vtex_app.config.get("api_credentials", {}).get("app_key"),
            "app_token": vtex_app.config.get("api_credentials", {}).get("app_token"),
            "domain": vtex_app.config.get("api_credentials", {}).get("domain"),
        }

        celery_app.send_task(
            name="task_insert_vtex_products",
            kwargs={"credentials": credentials, "catalog_uuid": str(catalog.uuid)},
            queue="product_first_synchronization",
        )

        return Response(CatalogSerializer(catalog).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        catalog = self.get_object()
        service = self.fb_service(catalog.app)
        connected_catalog_id = service.get_connected_catalog(catalog.app)
        serializer = self.serializer_class(
            catalog, context={"connected_catalog_id": connected_catalog_id}
        )
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page_data = self.paginate_queryset(queryset)
        serialized_data = []

        if queryset.exists():
            service = self.fb_service(queryset.first().app)
            connected_catalog_id = service.get_connected_catalog(queryset.first().app)
            serializer = CatalogListSerializer(
                page_data, context={"connected_catalog_id": connected_catalog_id}
            )
            serialized_data = serializer.data

        return self.get_paginated_response(serialized_data)

    @action(detail=True, methods=["GET"], url_path="list-products")
    def list_products(self, request, app_uuid, catalog_uuid, *args, **kwargs):
        catalog = self._get_catalog(catalog_uuid, app_uuid)
        queryset = catalog.products.all()
        page_data = self.paginate_queryset(queryset)
        serializer = ProductSerializer(page_data, many=True)

        return self.get_paginated_response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        catalog = self.get_object()
        service = self.fb_service(catalog.app)
        success = service.catalog_deletion(catalog)
        if not success:
            return Response(
                {"detail": "Failed to delete catalog on Facebook."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["POST"])
    def enable_catalog(self, request, *args, **kwargs):
        catalog = self.get_object()
        service = self.fb_service(catalog.app)
        success, response = service.enable_catalog(catalog)
        if not success:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=response)

        self.flows_service.update_catalog_to_active(
            catalog.app, catalog.facebook_catalog_id
        )
        return Response(status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"])
    def disable_catalog(self, request, *args, **kwargs):
        catalog = self.get_object()
        service = self.fb_service(catalog.app)
        success, response = service.disable_catalog(catalog)
        if not success:
            return Response(status=status.HTTP_400_BAD_REQUEST, data=response)

        self.flows_service.update_catalog_to_inactive(
            catalog.app, catalog.facebook_catalog_id
        )
        return Response(status=status.HTTP_200_OK)


class CommerceSettingsViewSet(BaseViewSet):
    serializer_class = ToggleVisibilitySerializer

    @action(detail=False, methods=["GET"])
    def commerce_settings_status(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        service = self.fb_service(app)
        response = service.wpp_commerce_settings(app)
        return Response(response)

    @action(detail=False, methods=["POST"])
    def toggle_catalog_visibility(self, request, app_uuid, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        enable_visibility = serializer.validated_data["enable"]

        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        service = self.fb_service(app)
        response = service.toggle_catalog_visibility(app, enable_visibility)
        return Response(response)

    @action(detail=False, methods=["POST"])
    def toggle_cart_visibility(self, request, app_uuid, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        enable_cart = serializer.validated_data["enable"]

        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        service = self.fb_service(app)
        response = service.toggle_cart(app, enable_cart)
        return Response(response)

    @action(detail=False, methods=["GET"])
    def get_active_catalog(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        service = self.fb_service(app)
        response = service.get_connected_catalog(app)
        return Response(response)


class TresholdViewset(BaseViewSet):
    serializer_class = TresholdSerializer

    @action(detail=True, methods=["POST"])
    def update_treshold(self, request, app_uuid, *args, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code="wpp-cloud")
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        treshold = serializer.validated_data["treshold"]
        self.flows_service.update_treshold(app, treshold)

        return Response(status=status.HTTP_204_NO_CONTENT)
