from marketplace.core.types.base import AppType
from marketplace.applications.models import App


class EmailAppType(AppType):
    platform = App.PLATFORM_WENI_FLOWS
    category = AppType.CATEGORY_EMAIL
    flows_type_code = "EM"
    description = "email.data.description"
    summary = "email.data.summary"
    developer = "Weni"

    def can_add(self, project_uuid: str) -> bool:
        return True
