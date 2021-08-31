from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.applications.models import App
from marketplace.grpc.client import ConnectGRPCClient
from .serializers import WeniWebChatSerializer, WeniWebChatConfigureSerializer
from . import type as type_


class WeniWebChatViewSet(viewsets.ModelViewSet):

    queryset = App.objects
    serializer_class = WeniWebChatSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return super().get_queryset().filter(app_code=type_.WeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(app_code=type_.WeniWebChatType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()

        self.serializer_class = WeniWebChatConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        channel_uuid = ConnectGRPCClient.create_weni_web_chat(request.user.email)
        serializer.validated_data["config"]["channelUuid"] = channel_uuid

        self.perform_update(serializer)

        self.generate_script()

        return Response(serializer.data)

    def generate_script(self):
        ...
