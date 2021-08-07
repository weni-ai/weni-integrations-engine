from django.urls import path, include
from rest_framework.routers import DefaultRouter

from marketplace.interactions import views as interactions_views


router = DefaultRouter()
router.register("comments", interactions_views.CommentViewSet, basename="comments")


urlpatterns = [
    path("apptypes/<str:app_code>/", include(router.urls)),
]
