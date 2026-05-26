"""URL routes for the Partner-led Account Verification flow."""

from django.urls import path

from .views import AccountVerificationView


urlpatterns = [
    path(
        "apps/<uuid:app_uuid>/account-verification/",
        AccountVerificationView.as_view(),
        name="wpp-cloud-account-verification",
    ),
]
