from typing import TYPE_CHECKING, Any

from decouple import config

from marketplace.clients.flows.client import FlowsClient
from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from marketplace.services.flows.service import FlowsService
from .views import WhatsAppDemoViewSet


if TYPE_CHECKING:
    from django.contrib.auth import get_user_model  # pragma: no cover

    User = get_user_model()  # pragma: no cover


class WhatsAppDemoType(AppType):
    view_class = WhatsAppDemoViewSet

    NUMBER = config("ROUTER_NUMBER")
    WABA_ID = config("ROUTER_WABA_ID")
    BUSINESS_ID = config("ROUTER_BUSINESS_ID")
    VERIFIED_NAME = config("ROUTER_VERIFIED_NAME")
    PHONE_NUMBER_ID = config("ROUTER_PHONE_NUMBER_ID")
    FACEBOOK_NAMESPACE = config("ROUTER_FACEBOOK_NAMESPACE")

    code = "wpp-demo"
    flows_type_code = "WAC"
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
    def configure_app(
        cls, app: App, user: "User", channel_token_client: Any
    ) -> App:
        config = dict(
            wa_number=cls.NUMBER,
            wa_verified_name=cls.VERIFIED_NAME,
            wa_waba_id=None,
            wa_currency="USD",
            wa_business_id=cls.BUSINESS_ID,
            wa_message_template_namespace=None,
            wa_pin=None,
        )

        flows_service = FlowsService(client=FlowsClient())
        channel = flows_service.create_wac_channel(
            user.email, str(app.project_uuid), cls.PHONE_NUMBER_ID, config
        )

        app.config["title"] = channel.get("name")
        app.flow_object_uuid = channel.get("uuid")
        app.config["wa_phone_number_id"] = cls.PHONE_NUMBER_ID
        app.config["has_insights"] = False

        channel_token = channel_token_client.get_channel_token(
            channel.get("uuid"), channel.get("name")
        )

        app.config["router_token"] = channel_token
        app.config["redirect_url"] = f"https://wa.me/{cls.NUMBER}?text={channel_token}"
        app.modified_by = user
        app.configured = True
        app.save()

        config["router_token"] = channel_token
        flows_service.update_config(config, app.flow_object_uuid)

        return app
