from django.urls import path, include
from rest_framework.routers import DefaultRouter

from marketplace.interactions import views


router = DefaultRouter()
router.register("feedbacks", views.FeedbackViewSet, basename="feedback")

urlpatterns = [
    path("", include(router.urls)),
]
