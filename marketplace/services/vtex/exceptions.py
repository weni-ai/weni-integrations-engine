from rest_framework import status  # TODO: Create status enumeration class
from rest_framework.exceptions import APIException


class NoVTEXAppConfiguredException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "There is no VTEX App configured."
    default_code = "no_vtex_app_configured"


class MultipleVTEXAppsConfiguredException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Multiple VTEX Apps are configured, which is not expected."
    default_code = "multiple_vtex_apps_configured"


class CredentialsValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The credentials provided are invalid."
    default_code = "invalid_credentials"
