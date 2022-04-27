from marketplace.core.types import views
from .serializers import WhatsAppDemoSerializer
from marketplace.celery import app as celery_app


class WhatsAppDemoViewSet(views.BaseAppTypeViewSet):

    serializer_class = WhatsAppDemoSerializer

    def get_queryset(self):
        return super().get_queryset().filter(code=self.type_class.code)

    def perform_create(self, serializer):

        user = self.request.user
        type_class = self.type_class
        instance = serializer.save(code=self.type_class.code)

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
        instance.config["redirect_url"] = f"https://wa.me/{type_class.NUMBER}?text={task.result}"
        instance.modified_by = user
        instance.save()
