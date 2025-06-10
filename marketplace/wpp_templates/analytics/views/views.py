from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from django.conf import settings

from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_templates.services.facebook import FacebookService
from marketplace.applications.models import App


class TemplateAnalyticsViewSet(viewsets.ViewSet):
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fb_service = None

    def fb_service(self, access_token: str):  # pragma: no cover
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class(access_token))
        return self._fb_service

    def get_app_service(self, app):
        if app.code == "wpp-cloud":
            access_token = app.apptype.get_access_token(app)
        else:
            access_token = settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
        return self.fb_service(access_token)

    def get_object(self) -> App:
        app_uuid = self.kwargs.get("app_uuid")
        return get_object_or_404(App, uuid=app_uuid, code__in=["wpp-cloud", "wpp"])

    @action(detail=True, methods=["POST"])
    def template_analytics(self, request, **kwargs):
        return Response({"detail": "This route has been moved"}, status=400)

    @action(detail=True, methods=["POST"])
    def enable_template_analytics(self, request, **kwargs):
        app = self.get_object()
        service = self.get_app_service(app)
        response = service.enable_insights(app)
        if response is None:
            return Response(
                {"detail": "Failed to activate template analytics"}, status=400
            )
        self._update_has_insights_key(app)

        return Response(status=200)

    def _update_has_insights_key(self, app):
        app.config["has_insights"] = True
        app.save()
