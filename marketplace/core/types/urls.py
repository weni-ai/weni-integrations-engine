from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types
from marketplace.core.types.channels.generic.views import DetailChannelType
from marketplace.core.types.channels.generic.views import GetIcons
from marketplace.core.types.channels.generic.views import GenericAppTypes

from marketplace.core.types.externals.generic.views import (
    DetailGenericExternals,
    ExternalsIcons,
    ExternalsAppTypes,
)

urlpatterns = []


for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()

    if apptype.view_class is None:
        continue

    router.register("apps", apptype.view_class, basename=f"{apptype.code}-app")
    urlpatterns.append(path(f"apptypes/{apptype.code}/", include(router.urls)))

router = routers.SimpleRouter()
# Channels
router.register("channel-type", DetailChannelType, basename="channel-type")
router.register("get-icons", GetIcons, basename="get-icons")
router.register("apptypes", GenericAppTypes, basename="my-apps")
# Externals
router.register("externals/detail", DetailGenericExternals, basename="externals-detail")
router.register("externals/icons", ExternalsIcons, basename="externals-icons")
router.register("externals/types", ExternalsAppTypes, basename="externals-types")

urlpatterns.append(path("apptypes/generic/", include(router.urls)))
