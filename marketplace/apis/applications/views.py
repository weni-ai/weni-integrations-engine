from rest_framework import viewsets
from rest_framework.response import Response


class AppTypeViewSet(viewsets.ViewSet):
    def list(self, request):
        ...

    def retrieve(self, request, pk=None):
        ...
