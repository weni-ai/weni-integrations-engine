from django.urls import path, include

urlpatterns = [
    path("webhook/", include("marketplace.webhooks.vtex.urls")),
]
