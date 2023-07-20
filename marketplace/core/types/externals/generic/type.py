from .views import GenericExternalsViewSet

from marketplace.interfaces.flows import FlowsInterface

from marketplace.core.types.base import AppType, GenericAppType
from marketplace.core.types.externals.generic.views import (
    DetailGenericExternals,
    ExternalsIcons,
    ExternalsAppTypes,
)


class GenericExternalAppType(GenericAppType):
    view_class = GenericExternalsViewSet
    category = AppType.CATEGORY_EXTERNAL
    code = "generic-external"

    EXTRA_VIEWS = [
        ("detail", DetailGenericExternals, "externals-detail"),
        ("icons", ExternalsIcons, "externals-icons"),
        ("types", ExternalsAppTypes, "externals-types"),
    ]

    @classmethod
    def get_extra_urls(cls, router):
        for route, view, basename in cls.EXTRA_VIEWS:
            router.register(route, view, basename=basename)

    @classmethod
    def list(cls, client: FlowsInterface, flows_type_code=None):
        return client.list_external_types(flows_type_code)

    @classmethod
    def release(cls, client: FlowsInterface, uuid: str, user_email: str):
        return client.release_external_service(uuid, user_email)

    @classmethod
    def create(
        cls,
        client: FlowsInterface,
        user: str,
        project_uuid: str,
        attrs: dict,
        external_code: str,
    ):
        return client.create_external_service(user, project_uuid, attrs, external_code)
