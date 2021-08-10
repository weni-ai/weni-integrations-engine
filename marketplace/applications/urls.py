from django.urls import path, include
from rest_framework_nested import routers

from marketplace.applications import views as applications_views
from marketplace.interactions import views as interactions_views


router = routers.SimpleRouter()
router.register("apptypes", applications_views.AppTypeViewSet, basename="apptype")

comments_router = routers.NestedSimpleRouter(router, r"apptypes", lookup="apptype")
comments_router.register("comments", interactions_views.CommentViewSet, basename="apptype-comment")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(comments_router.urls)),
]
