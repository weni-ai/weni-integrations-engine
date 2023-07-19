from typing import TYPE_CHECKING, Any

from decouple import config

from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import WhatsAppDemoViewSet


if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class WhatsAppDemoType(AppType):
    view_class = WhatsAppDemoViewSet

    NUMBER = config("ROUTER_NUMBER")
    COUNTRY = config("ROUTER_COUNTRY", "BR")
    BASE_URL = config("ROUTER_BASE_URL")
    USERNAME = config("ROUTER_USERNAME")
    PASSWORD = config("ROUTER_PASSWORD")
    FACEBOOK_NAMESPACE = config("ROUTER_FACEBOOK_NAMESPACE")

    code = "wpp-demo"
    flows_type_code = "WA"
    name = "WhatsApp Demo"
    description = "WhatsAppDemo.data.description"
    summary = "WhatsAppDemo.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"

    def can_add(self, project_uuid: str) -> bool:
        return not App.objects.filter(
            code=self.code, project_uuid=project_uuid
        ).exists()

    def template_type_setup(self) -> dict:
        return dict(code=self.code)

    @classmethod
    def configure_app(cls, app: App, user: "User", channel_client: Any, channel_token_client: Any) -> App:
        data = dict(
            number=cls.NUMBER,
            country=cls.COUNTRY,
            base_url=cls.BASE_URL,
            username=cls.USERNAME,
            password=cls.PASSWORD,
            facebook_namespace=cls.FACEBOOK_NAMESPACE,
            facebook_template_list_domain="graph.facebook.com",
            facebook_business_id="null",
            facebook_access_token="null",
        )

        channel = channel_client.create_channel(user.email, str(app.project_uuid), data, app.channeltype_code)

        app.config["title"] = channel.get("name")
        app.flow_project_uuid = channel.get("uuid")

        channel_token = channel_token_client.get_channel_token(channel.get("uuid"), channel.get("name"))

        app.config["routerToken"] = channel_token
        app.config["redirect_url"] = f"https://wa.me/{cls.NUMBER}?text={channel_token}"
        app.modified_by = user
        app.save()

        return app
