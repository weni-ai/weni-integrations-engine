from rest_framework.decorators import action
from rest_framework.response import Response

from weni_commons.auth import WeniAuthViewMixin

from .serializers import WeniWebChatSerializer, WeniWebChatConfigureSerializer
from marketplace.accounts.authentication import WeniModuleAuthentication
from marketplace.accounts.permissions import ProjectManagePermission
from marketplace.core.types import views
from . import type as type_


class WeniWebChatViewSet(WeniAuthViewMixin, views.BaseAppTypeViewSet):
    serializer_class = WeniWebChatSerializer
    authentication_classes = [WeniModuleAuthentication]
    permission_classes = [ProjectManagePermission]

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.WeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.WeniWebChatType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        self.serializer_class = WeniWebChatConfigureSerializer
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)
