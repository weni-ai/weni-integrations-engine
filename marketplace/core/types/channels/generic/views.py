"""  this view manages all available channels configuring them in a generic way """

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework import viewsets

from .serializers import GenericChannelSerializer, GenericConfigureSerializer
from marketplace.core.types import views
from marketplace.connect.client import ConnectProjectClient
from . import type as type_

class GenericChannelViewSet(views.BaseAppTypeViewSet):
    """ Generic channel create and listing """
    serializer_class = GenericChannelSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.GenericType.code)

    def perform_create(self, serializer):
        channel_code = self.request.data.get("channel_code", None)
        channel_name = self.request.data.get("channel_name", None)
        if channel_code:
            channel_code = channel_code.strip()

        if not channel_code:
            raise serializers.ValidationError('Code not be empty.')

        instance = serializer.save(code="generic")
        instance.config["channel_code"] = channel_code
        instance.modified_by = self.request.user
        instance.name = channel_name
        instance.save()

    @action(detail=True, methods=["PATCH"])
    def configure(self, request):
        """ Add the generic channel in weni-flows """
        self.serializer_class = GenericConfigureSerializer
        data = request.data
        serializer = self.get_serializer(self.get_object(), data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class DetailChannels(viewsets.ViewSet):
    lookup_field = "code_channel"

    def retrieve(self, request, code_channel=None):
        client = ConnectProjectClient()
        return Response(client.get_available_channel(channel_code=code_channel))
