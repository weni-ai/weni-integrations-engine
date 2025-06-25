from django.urls import path, include
from rest_framework_nested import routers

from marketplace.core import types
from marketplace.core.types.channels.whatsapp_cloud.views import WhatsAppCloudInsights


urlpatterns = []


for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()
    if apptype.view_class is None:
        continue

    router.register("apps", apptype.view_class, basename=f"{apptype.code}-app")
    urlpatterns.append(path(f"apptypes/{apptype.code}/", include(router.urls)))


urlpatterns.append(
    path("apptypes/generic/", include("marketplace.core.types.channels.generic.urls")),
)

urlpatterns.append(
    path(
        "apptypes/wpp-cloud/",
        include("marketplace.core.types.channels.whatsapp_cloud.catalogs.urls"),
    )
)

urlpatterns.append(
    path(
        "apptypes/wpp-cloud/list_wpp-cloud/<uuid:project_uuid>/",
        WhatsAppCloudInsights.as_view(),
        name="wpp-cloud-insights",
    )
)
# Facebook
urlpatterns.append(
    path(
        "apptypes/facebook/", include("marketplace.core.types.channels.facebook.urls")
    ),
)
# VTEX
urlpatterns.append(
    path("apptypes/vtex/", include("marketplace.core.types.ecommerce.vtex.urls")),
)
