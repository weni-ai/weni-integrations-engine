from django.db.models import Q
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from marketplace.applications.serializers import AppTypeSerializer, MyAppSerializer
from marketplace.core import types
from marketplace.applications.models import App


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


class MyAppViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "uuid"
    serializer_class = MyAppSerializer
    queryset = App.objects

    def get_queryset(self):
        queryset = super().get_queryset()

        query_params = self.request.query_params
        project_uuid = query_params.get("project_uuid")
        configured = query_params.get("configured")

        if not project_uuid:
            raise ValidationError("project_uuid is a required parameter!")

        queryset = queryset.filter(project_uuid=project_uuid)

        if configured is not None:
            if configured == "true":
                queryset = queryset.exclude(config={})

            elif configured == "false":
                queryset = queryset.filter(config={})

            else:
                raise ValidationError(f"Expected a boolean param in configured, but recived `{configured}`")

        # TODO: Validate user permission

        return queryset
