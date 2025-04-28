from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from marketplace.core.types import views
from marketplace.core.types.channels.new_weni_web_chat.serializers import (
    NewWeniWebChatConfigureSerializer,
    NewWeniWebChatSerializer,
)
from marketplace.core.types.channels.new_weni_web_chat.type import NewWeniWebChatType
from marketplace.core.types.channels.new_weni_web_chat.usecases import (
    ConfigureNewWeniWebChatUseCase,
)


class NewWeniWebChatViewSet(views.BaseAppTypeViewSet):
    serializer_class = NewWeniWebChatSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=NewWeniWebChatType.code)

    def perform_create(self, serializer):
        serializer.save(code=NewWeniWebChatType.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        serializer_class = NewWeniWebChatConfigureSerializer

        app_instance = self.get_object()

        serializer = serializer_class(app_instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        usecase = ConfigureNewWeniWebChatUseCase(app_instance, request.user)
        processed_config = usecase.execute(serializer.validated_data["config"])

        app_instance.config = processed_config
        app_instance.save(update_fields=["config"])

        return Response(serializer_class(app_instance).data, status=status.HTTP_200_OK)
