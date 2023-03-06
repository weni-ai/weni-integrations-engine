from rest_framework.decorators import action
from rest_framework.response import Response

from .serializers import OmieSerializer, OmieConfigureSerializer
from marketplace.core.types import views


class OmieViewSet(views.BaseAppTypeViewSet):

    serializer_class = OmieSerializer

    def get_queryset(self):
        # TODO: Send the responsibility of this method to the BaseAppTypeViewSet
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        print("chamando")
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        app = self.get_object()

        self.serializer_class = OmieConfigureSerializer
        serializer = self.get_serializer(app, data=request.data)
        serializer.is_valid(raise_exception=True)
        config = serializer.validated_data.get("config")

        self.type_class.update_app(app, request.user, config)

        self.perform_update(serializer)

        return Response(serializer.data)
