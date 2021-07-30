from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

from marketplace.applications.serializers import AppTypeSerializer
from marketplace.core import types


class AppTypeViewSet(viewsets.ViewSet):

    serializer_class = AppTypeSerializer

    def list(self, request):
        app_types = types.get_types(request.query_params.get("category"))
        serializer = self.serializer_class(app_types, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            app_type = types.get_type(pk)
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(app_type)

        return Response(serializer.data)
