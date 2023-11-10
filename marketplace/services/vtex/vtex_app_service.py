"""
Service for retrieving a configured VTEX App instance by its project UUID.

This service is responsible for finding an App instance with a specific 'vtex' code
within the project identified by the provided UUID. It ensures that only one configured
VTEX App is associated with the project and raises exceptions if the App is not found
or if multiple Apps are found.

Methods:
    get_vtex_app_or_error(project_uuid): Retrieves a VTEX App instance or raises
    an HTTP exception if the App cannot be found or if there are multiple Apps.

Raises:
    NotFound: An error is raised as an HTTP 404 Not Found if no VTEX App is configured
    for the given project UUID.

    APIException: An error is raised as an HTTP 400 Bad Request if multiple configured
    VTEX Apps are found for the given project UUID, which is unexpected behavior.
"""
from rest_framework.exceptions import APIException
from rest_framework import status

from django.core.exceptions import MultipleObjectsReturned

from marketplace.applications.models import App


class VtexAppService:
    @staticmethod
    def get_vtex_app_or_error(project_uuid):
        try:
            app_vtex = App.objects.get(
                code="vtex", project_uuid=str(project_uuid), configured=True
            )
            return app_vtex
        except App.DoesNotExist:
            exception = APIException("There is no VTEX App configured.")
            exception.status_code = status.HTTP_404_NOT_FOUND
            raise exception
        except MultipleObjectsReturned:
            exception = APIException(
                "Multiple VTEX Apps are configured, which is not expected."
            )
            exception.status_code = status.HTTP_400_BAD_REQUEST
            raise exception
