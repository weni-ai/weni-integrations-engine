from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action

from marketplace.core import serializers, types
from marketplace.applications.models import App
from .serializers import WeniWebChatSerializer, WeniWebChatConfigureSerializer
from . import type as type_


class WeniWebChatViewSet(viewsets.ModelViewSet):

    queryset = App.objects
    serializer_class = WeniWebChatSerializer

    def get_queryset(self):
        return super().get_queryset().filter(app_code=type_.WeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(app_code=type_.WeniWebChatType.code)

    @action(detail=True, methods=["PUT"], serializer_class=WeniWebChatConfigureSerializer)
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)
