from rest_framework.decorators import action
from rest_framework.response import Response

from marketplace.core.types import views
from .serializers import WhatsAppDemoSerializer
from marketplace.celery import app as celery_app


class WhatsAppDemoViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppDemoSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):
        serializer.save(code=self.type_class.code)

    @action(detail=True, methods=["PATCH"])
    def configure(self, request, **kwargs):
        """
        Adds a config on specified App and create a channel on weni-flows
        """
        user = request.user
        instance = self.get_object()
        type_class = self.type_class

        data = dict(
            number=type_class.NUMBER,
            country=type_class.COUNTRY,
            base_url=type_class.BASE_URL,
            username=type_class.USERNAME,
            password=type_class.PASSWORD,
            facebook_namespace=type_class.FACEBOOK_NAMESPACE,
            facebook_template_list_domain="graph.facebook.com",
            facebook_business_id="null",
            facebook_access_token="null",
        )

        task = celery_app.send_task(
            name="create_channel", args=[user.email, str(instance.project_uuid), data, instance.channeltype_code]
        )
        task.wait()

        result = task.result

        instance.config["title"] = result.get("name")
        instance.config["channelUuid"] = result.get("uuid")

        task = celery_app.send_task(name="get_channel_token", args=[result.get("uuid"), result.get("name")])
        task.wait()

        instance.config["routerToken"] = task.result
        instance.config["redirectUrl"] = f"https://wa.me/{type_class.NUMBER}?text={task.result}"
        instance.modified_by = user
        instance.save()

        return Response(dict(uuid=str(instance.uuid), redirectUrl=instance.config["redirectUrl"]))
