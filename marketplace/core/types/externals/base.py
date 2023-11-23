from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class ExternalAppType(AppType):
    platform = App.PLATFORM_WENI_FLOWS
    category = AppType.CATEGORY_EXTERNAL
