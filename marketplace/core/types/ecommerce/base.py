from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class EcommerceAppType(AppType):
    platform = App.PLATFORM_VTEX
    category = AppType.CATEGORY_ECOMMERCE
