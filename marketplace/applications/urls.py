from django.urls import path, include
from rest_framework.routers import DefaultRouter
from marketplace.applications import views as applications_views


router = DefaultRouter()
router.register("apptypes", applications_views.AppTypeViewSet, basename="apptypes")

urlpatterns = [
    path("", include(router.urls)),
]
