from rest_framework import viewsets

from marketplace.applications.models import App
from .serializers import WeniWebChatSerializer
from . import type as type_


class WeniWebChatViewSet(viewsets.ModelViewSet):

    queryset = App.objects
    serializer_class = WeniWebChatSerializer
    lookup_field = "uuid"

    def get_queryset(self):
        return super().get_queryset().filter(code=type_.WeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(code=type_.WeniWebChatType.code)
