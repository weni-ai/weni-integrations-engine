from django.urls import path, include
from rest_framework import routers

from marketplace.wpp_templates import views

router = routers.SimpleRouter()
router.register("templates", views.TemplateMessageViewSet, basename="templates")

urlpatterns = [
    path("", include(router.urls))
]
