from rest_framework import viewsets
from django.conf import settings

from marketplace.applications.models import App
from marketplace.accounts.permissions import ProjectManagePermission
from marketplace.celery import app as celery_app


class BaseAppTypeViewSet(viewsets.ModelViewSet):

    queryset = App.objects
    lookup_field = "uuid"
    permission_classes = [ProjectManagePermission]

    def perform_destroy(self, instance):
        super().perform_destroy(instance)

        channel_uuid = instance.config.get("channelUuid")

        if channel_uuid is not None and settings.USE_GRPC:
            celery_app.send_task(name="release_channel", args=[channel_uuid, self.request.user.email]).wait()
