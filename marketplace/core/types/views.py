from typing import TYPE_CHECKING

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.applications.models import App

if TYPE_CHECKING:
    from marketplace.core.types.base import AppType


class BaseAppTypeViewSet(viewsets.ModelViewSet):

    queryset = App.objects
    type_class: "AppType" = None
    lookup_field = "uuid"

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs) -> Response:
        raise NotImplementedError()
