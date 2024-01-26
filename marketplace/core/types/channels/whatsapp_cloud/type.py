from django.conf import settings
from marketplace.core.types.base import AppType
from marketplace.applications.models import App
from .views import WhatsAppCloudViewSet


class WhatsAppCloudType(AppType):
    view_class = WhatsAppCloudViewSet
    code = "wpp-cloud"
    flows_type_code = "WAC"
    name = "WhatsApp"
    description = "WhatsAppCloud.data.description"
    summary = "WhatsAppCloud.data.summary"
    category = AppType.CATEGORY_CHANNEL
    developer = "Weni"
    bg_color = "#d1fcc9cc"  # TODO: Change to real color
    platform = App.PLATFORM_WENI_FLOWS
    config_design = "popup"

    def get_access_token(self, app: App):
        user_token = app.config.get("wa_user_token")
        if user_token:
            return user_token
        return settings.WHATSAPP_SYSTEM_USER_ACCESS_TOKEN
