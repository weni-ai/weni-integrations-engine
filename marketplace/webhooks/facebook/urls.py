from django.urls import path
from .views import FacebookWebhook

urlpatterns = [
    path(
        "facebook/api/notification/",
        FacebookWebhook.as_view(),
        name="facebook-updates",
    ),
]
