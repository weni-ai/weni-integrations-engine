from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.views import APIView

from marketplace.core.types.ecommerce.vtex.serializers import (
    VtexAdsSerializer,
    VtexSerializer,
    VtexAppSerializer,
    VtexSyncSellerSerializer,
)
from marketplace.core.types import views
from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)
from marketplace.services.vtex.generic_service import VtexServiceBase
from marketplace.services.vtex.generic_service import APICredentials
from marketplace.services.flows.service import FlowsService
from marketplace.clients.flows.client import FlowsClient
from marketplace.services.vtex.app_manager import AppVtexManager
from marketplace.wpp_products.utils import SellerSyncUtils
from marketplace.accounts.permissions import ProjectManagePermission


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
        serializer.save(code=self.type_class.code, uuid=serializer.initial_data["uuid"])

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
        store_domain = validated_data["store_domain"]

        self.service.check_is_valid_credentials(credentials)

        # Calls the create method of the base class to create the App object
        response = super().create(request, *args, **kwargs)
        app = self.get_app()
        if not app:
            return response

        try:
            updated_app = self.service.configure(
                app, credentials, wpp_cloud_uuid, store_domain
            )
            self.flows_service.update_vtex_integration_status(
                app.project_uuid, app.created_by.email, action="POST"
            )
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
        app = self.get_object()
        success = self.service.synchronized_sellers(app=app, sellers_id=sellers_id)
        if not success:
            return Response(
                data={"message": "failure to start synchronization"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_200_OK)

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


class VtexIntegrationDetailsView(APIView):
    permission_classes = [ProjectManagePermission]

    def get(self, request, project_uuid):
        integration_details = VtexIntegration.vtex_integration_detail(
            project_uuid=project_uuid
        )
        return Response(status=status.HTTP_200_OK, data=integration_details)
