from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework import status
from django.conf import settings

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_templates.services.facebook import FacebookService
from marketplace.applications.models import App
from marketplace.wpp_templates.analytics.serializers import AnalyticsSerializer


class TemplateAnalyticsViewSet(viewsets.ViewSet):
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fb_service = None
        self._access_token = None

    def fb_service(self, access_token: str):  # pragma: no cover
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class(access_token))

        return self._fb_service

    def get_object(self) -> App:
        app_uuid = self.kwargs.get("app_uuid")
        return get_object_or_404(App, uuid=app_uuid, code__in=["wpp-cloud", "wpp"])
    @action(detail=True, methods=["GET"])
    def template_analytics(self, request, app_uuid=None, **kwargs):
        app = get_object_or_404(App, uuid=app_uuid, code__in=["wpp-cloud", "wpp"])
        if app.code == "wpp-cloud":
            service = self.fb_service(app.apptype.get_access_token(app))
        else:
            service = self.fb_service(settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN)

        serializer = AnalyticsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        response = service.template_analytics(app, validated_data)
        return Response(response)

    @action(detail=True, methods=["POST"])
    def enable_template_analytics(self, request, **kwargs):
        response = self.fb_service.enable_insights(self.get_object())
        if response is None:
            return Response(
                {"detail": "Failed to activate template analytics"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        self._update_has_insights_key(self.get_object())
        return Response(status=status.HTTP_200_OK)

    def _update_has_insights_key(self, app):
        app.config["has_insights"] = True
        app.save()
