from django.urls import path, include
from rest_framework_nested import routers

from marketplace.applications import views as applications_views
from marketplace.interactions import views as interactions_views


router = routers.SimpleRouter()
router.register("apptypes", applications_views.AppTypeViewSet, basename="apptypes")

comments_router = routers.NestedSimpleRouter(router, r"apptypes", lookup="apptypes")
comments_router.register("comments", interactions_views.CommentViewSet, basename="apptypes-comments")


urlpatterns = [
    path("", include(router.urls)),
    path("", include(comments_router.urls)),
]
