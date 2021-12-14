from rest_framework.decorators import action

from marketplace.core.types import views
from .serializers import WhatsAppDemoSerializer
from . import type as type_


class WhatsAppDemoViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppDemoSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.WeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.WeniWebChatType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        ...
