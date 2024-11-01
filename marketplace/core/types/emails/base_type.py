from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class EmailAppType(AppType):
    platform = App.PLATFORM_WENI_FLOWS
    category = AppType.CATEGORY_EMAIL
    flows_type_code = "EM"
    name = "Email"
    description = "email.data.description"
    summary = "email.data.summary"
    developer = "Weni"
    bg_color = "#039be533"
    config_design = "popup"
