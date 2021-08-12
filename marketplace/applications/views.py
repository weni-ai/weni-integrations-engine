from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status

from marketplace.applications.serializers import AppTypeSerializer
from marketplace.core import types


class AppTypeViewSet(viewsets.ViewSet):

    serializer_class = AppTypeSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = {"request": self.request}
        return self.serializer_class(*args, **kwargs)

    def list(self, request):
        app_types = types.get_types(request.query_params.get("category"))
        serializer = self.get_serializer(app_types, many=True)

        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            app_type = types.get_type(pk)
        except KeyError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(app_type)

        return Response(serializer.data)
