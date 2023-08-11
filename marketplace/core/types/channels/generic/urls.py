from rest_framework.routers import SimpleRouter
from .views import (
    DetailChannelType,
    GetIcons,
    GenericAppTypes,
)

router = SimpleRouter()
router.register("channel-type", DetailChannelType, basename="channel-type")
router.register("get-icons", GetIcons, basename="get-icons")
router.register("apptypes", GenericAppTypes, basename="my-apps")

urlpatterns = router.urls
