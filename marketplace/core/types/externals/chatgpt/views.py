from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action

from marketplace.flows.client import FlowsClient

from .serializers import (
    ChatGPTSerializer,
    ChatGPTCreateSerializer,
)
from marketplace.core.types import views
from marketplace.applications.models import App
from marketplace.core.models import Prompt


class ChatGPTViewSet(views.BaseAppTypeViewSet):
    serializer_class = ChatGPTSerializer

    def create(self, request, *args, **kwargs):
        serializer = ChatGPTCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        project_uuid = request.data.pop("project_uuid")
        type_code = "chatgpt"
        config_data = request.data

        client = FlowsClient()
        response = client.create_external_service(
            request.user.email, (project_uuid), config_data, type_code
        )
        flows_data = response.json()
        app = App.objects.create(
            code=type_code,
            config=config_data,
            project_uuid=project_uuid,
            configured=True,
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=request.user,
            flow_object_uuid=flows_data.get("uuid"),
        )
        serializer.validated_data["uuid"] = str(app.uuid)
        return Response(serializer.validated_data, response.status_code)

    def update(self, request, *args, **kwargs):
        app = self.get_object()
        client = FlowsClient()
        update_config = request.data.get("config")

        if update_config:
            detail_channel = client.detail_external(app.flow_object_uuid)
            flows_config = detail_channel["config"]
            for key, value in update_config.items():
                flows_config[key] = value

            client.update_external_config(
                data=flows_config, flow_object_uuid=app.flow_object_uuid
            )
            app.config = flows_config
            app.save()

        serializer = self.get_serializer(app)
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

    @action(detail=True, methods=["POST", "GET", "DELETE"])
    def prompts(self, request, **kwargs):
        app = self.get_object()
        client = FlowsClient()
        user = request.user.email
        created_prompts = []
        if request.method == "POST":
            for prompt in request.data.get("prompts"):
                text = prompt.get("text")
                response = client.create_prompts(
                    user=user, text=text, external_uuid=app.flow_object_uuid
                )
                prompt_uuid = response.json()["uuid"]
                Prompt.objects.create(app=app, text=text, uuid=prompt_uuid)
                created_prompts.append(response.json())

            return Response(created_prompts, response.status_code)

        elif request.method == "DELETE":
            for prompt_uuid in request.data.get("prompts"):
                response = client.delete_prompts(
                    prompt_uuid=prompt_uuid,
                    external_uuid=app.flow_object_uuid,
                )

            Prompt.objects.filter(
                app=app, uuid__in=request.data.get("prompts")
            ).delete()
            return Response(status=response.status_code)
        elif request.method == "GET":
            response = client.list_prompts(external_uuid=app.flow_object_uuid)
            return Response(response.json(), response.status_code)
