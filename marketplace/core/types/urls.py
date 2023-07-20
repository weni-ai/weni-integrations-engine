from rest_framework_nested import routers

from marketplace.core import types

urlpatterns = []

for apptype in types.APPTYPES.values():
    router = routers.SimpleRouter()
    urlpatterns = apptype.get_urls(router, urlpatterns)
