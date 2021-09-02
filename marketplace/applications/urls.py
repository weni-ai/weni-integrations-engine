from django.urls import path, include
from rest_framework_nested import routers

from marketplace.applications import views as applications_views
from marketplace.interactions import views as interactions_views
from marketplace.core.types import urls as apps_urls


router = routers.SimpleRouter()
router.register("apptypes", applications_views.AppTypeViewSet, basename="apptype")
router.register("my-apps", applications_views.MyAppViewSet, basename="my-app")

comments_router = routers.NestedSimpleRouter(router, r"apptypes", lookup="apptype")
comments_router.register("comments", interactions_views.CommentViewSet, basename="apptype-comment")

rating_router = routers.NestedSimpleRouter(router, r"apptypes", lookup="apptype")
rating_router.register("ratings", interactions_views.RatingViewSet, basename="apptype-rating")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(comments_router.urls)),
    path("", include(rating_router.urls)),
    path("", include(apps_urls)),
]
