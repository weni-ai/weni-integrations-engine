from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.connect.client import ConnectProjectClient
from marketplace.flows.client import FlowsClient

from .serializers import OmieSerializer, OmieConfigureSerializer
from marketplace.core.types import views


class OmieViewSet(views.BaseAppTypeViewSet):

    serializer_class = OmieSerializer

    def get_queryset(self):
        # TODO: Send the responsibility of this method to the BaseAppTypeViewSet
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        app = self.get_object()

        self.serializer_class = OmieConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)

    def perform_destroy(self, instance):
        channel_uuid = instance.config.get("channelUuid")
        if channel_uuid:
            client = FlowsClient()
            client.release_external_service(channel_uuid, self.request.user.email)

        super().perform_destroy(instance)
