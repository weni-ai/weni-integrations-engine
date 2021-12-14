from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import TelegramSerializer, TelegramConfigureSerializer
from marketplace.core.types import views
from . import type as type_


class TelegramViewSet(views.BaseAppTypeViewSet):

    serializer_class = TelegramSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.TelegramType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.TelegramType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        self.serializer_class = TelegramConfigureSerializer
        serializer = self.get_serializer(self.get_object(), data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        return Response(serializer.data)
