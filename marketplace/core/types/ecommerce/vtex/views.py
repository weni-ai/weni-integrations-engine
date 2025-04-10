from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.views import APIView

from marketplace.core.types.ecommerce.vtex.serializers import (
    FirstProductInsertSerializer,
    VtexAdsSerializer,
    CreateVtexSerializer,
    VtexAppSerializer,
    VtexSyncSellerSerializer,
)
from marketplace.core.types import views
from marketplace.core.types.ecommerce.vtex.usecases.link_catalog_start_sync import (
    LinkCatalogAndStartSyncUseCase,
)
from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)
from marketplace.services.vtex.generic_service import VtexServiceBase
from marketplace.services.flows.service import FlowsService
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.vtex.app_manager import AppVtexManager
from marketplace.wpp_products.utils import SellerSyncUtils
from marketplace.accounts.permissions import ProjectManagePermission
from marketplace.core.types.ecommerce.vtex.usecases.create_vtex_integration import (
    CreateVtexIntegrationUseCase,
)
from marketplace.core.types.ecommerce.vtex.publisher.vtex_app_created_publisher import (
    VtexAppCreatedPublisher,
)


class VtexViewSet(views.BaseAppTypeViewSet):
    serializer_class = VtexAppSerializer
    service_class = VtexServiceBase
    flows_service_class = FlowsService
    flows_client = FlowsClient
    app_manager_class = AppVtexManager

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._service = None
        self._flows_service = None
        self._app_manager = None

    @property
    def service(self):  # pragma: no cover
        if not self._service:
            self._service = self.service_class()
        return self._service

    @property
    def flows_service(self):  # pragma: no cover
        if not self._flows_service:
            self._flows_service = self.flows_service_class(self.flows_client())
        return self._flows_service

    @property
    def app_manager(self):  # pragma: no cover
        if not self._app_manager:
            self._app_manager = self.app_manager_class()
        return self._app_manager

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    def create(self, request, *args, **kwargs):
        serializer = CreateVtexSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = super().create(request, *args, **kwargs)

        app = self.get_app()

        if not app:
            return response

        configured_app = CreateVtexIntegrationUseCase.configure_app(
            app, serializer.validated_data
        )

        serialized_app = self.get_serializer(configured_app)

        publisher = VtexAppCreatedPublisher()
        success = publisher.create_event(serialized_app.data)

        if not success:
            return Response(
                {"error": "Faile to publish Vtex app creation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            data=serialized_app.data,
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        self.flows_service.update_vtex_integration_status(
            instance.project_uuid, instance.created_by.email, action="DELETE"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["GET"], url_path="get-app-uuid")
    def get_app_uuid(self, request, *args, **kwargs):
        uuid = self.app_manager.get_vtex_app_uuid()
        return Response(data={"uuid": uuid}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["POST"], url_path="sync-vtex-sellers")
    def sync_sellers(self, request, uuid=None, *args, **kwargs):
        serializer = VtexSyncSellerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        sellers_id = validated_data.get("sellers")
        sync_all_sellers = validated_data.get("sync_all_sellers", False)

        app = self.get_object()
        success = self.service.synchronized_sellers(
            app=app, sellers_id=sellers_id, sync_all_sellers=sync_all_sellers
        )

        if not success:
            return Response(
                data={"message": "failure to start synchronization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            data={"message": "synchronization started successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["GET"], url_path="active-vtex-sellers")
    def active_sellers(self, request, uuid=None, *args, **kwargs):
        response = self.service.active_sellers(self.get_object())
        return Response(data=response, status=status.HTTP_200_OK)

    @action(detail=True, methods=["GET"], url_path="check-sync-sellers")
    def check_sync_status(self, request, uuid=None, *args, **kwargs):
        app = self.get_object()
        vtex_app_uuid = str(app.uuid)
        lock_key = f"sync-sellers:{vtex_app_uuid}"
        lock_data = SellerSyncUtils.get_lock_data(lock_key)

        if lock_data:
            return Response(
                data={
                    "message": "A synchronization is already in progress",
                    "data": lock_data,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            data={"message": "No synchronization in progress"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["POST"], url_path="update-vtex-ads")
    def update_vtex_ads(self, request, app_uuid=None, *args, **kwargs):
        app = self.get_object()
        serializer = VtexAdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        vtex_ads = serializer.validated_data["vtex_ads"]

        self.app_manager.update_vtex_ads(app, serializer.validated_data["vtex_ads"])

        self.flows_service.update_vtex_ads_status(app, vtex_ads, action="POST")
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["POST"], url_path="link-catalog")
    def link_catalog(self, request, uuid=None, *args, **kwargs):
        """
        Link a catalog to the VTEX app and trigger product synchronization.

        Expected payload:
            {
                "catalog_id": "<catalog identifier>"
                "domain": "<catalog domain>"
                "store_domain": "<store domain>"
                "app_key": "<app key>"
                "app_token": "<app token>"
                "wpp_cloud_uuid": "<wpp cloud identifier>"
            }

        Returns:
            200 OK if the task is dispatched successfully, or 400 Bad Request on error.
        """
        serializer = FirstProductInsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        catalog_id = validated_data.get("catalog_id")

        try:
            vtex_app = self.get_object()
        except Exception:
            return Response(
                {"error": "VTEX app not found"}, status=status.HTTP_404_NOT_FOUND
            )

        use_case = LinkCatalogAndStartSyncUseCase(vtex_app)
        use_case.configure_catalog(validated_data)
        success = use_case.link_catalog(catalog_id=catalog_id)

        if not success:
            return Response(
                {"error": "Failed to link catalog and start product synchronization"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "message": "Catalog linked and synchronization task dispatched successfully"
            },
            status=status.HTTP_200_OK,
        )


class VtexIntegrationDetailsView(APIView):
    permission_classes = [ProjectManagePermission]

    def get(self, request, project_uuid):
        integration_details = VtexIntegration.vtex_integration_detail(
            project_uuid=project_uuid
        )
        return Response(status=status.HTTP_200_OK, data=integration_details)
