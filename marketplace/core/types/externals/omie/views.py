from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from marketplace.flows.client import FlowsClient

from .serializers import OmieSerializer, OmieConfigureSerializer
from marketplace.core.types import views


class OmieViewSet(views.BaseAppTypeViewSet):
    serializer_class = OmieSerializer

    def get_queryset(self):
        # TODO: Send the responsibility of this method to the BaseAppTypeViewSet
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        app = self.get_object()
        self.serializer_class = OmieConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_update(serializer)

        if app.flow_object_uuid is None:
            validated_config = serializer.validated_data.get("config")

            payload = {
                "name": validated_config.get("name"),
                "app_key": validated_config.get("app_key"),
                "app_secret": validated_config.get("app_secret"),
            }

            user = request.user
            client = FlowsClient()

            response = client.create_external_service(
                user.email, str(app.project_uuid), payload, app.flows_type_code
            )
            app.flow_object_uuid = response.json().get("uuid")
            app.save()

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        channel_uuid = instance.flow_object_uuid
        if channel_uuid:
            client = FlowsClient()
            client.release_external_service(channel_uuid, self.request.user.email)

        instance.delete()
