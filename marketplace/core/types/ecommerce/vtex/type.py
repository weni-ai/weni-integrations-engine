from marketplace.applications.models import App
from ..base import EcommerceAppType
from .views import VtexViewSet


class VtexType(EcommerceAppType):
    view_class = VtexViewSet
    code = "vtex"
    flows_type_code = None
    name = "Vtex"
    description = "vtex.data.description"
    summary = "vtex.data.summary"
    bg_color = None
    developer = "Weni"
    config_design = "pre-popup"

    def can_add(self, project_uuid: str) -> bool:
        return not App.objects.filter(
            code=self.code, project_uuid=project_uuid
        ).exists()
