from decouple import config

from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import WhatsAppDemoViewSet


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
