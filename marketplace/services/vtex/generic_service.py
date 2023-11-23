"""
Service for managing VTEX App instances within a project.

This service provides methods to retrieve a configured VTEX App instance by its project UUID,
validate API credentials, and configure a VTEX App instance with provided credentials.

Attributes:
    None

Methods:
    get_vtex_app_or_error(project_uuid): Retrieves a single configured VTEX App instance
        associated with the provided project UUID or raises an exception if not found or if
        multiple instances are found.

    check_is_valid_credentials(credentials): Validates the provided API credentials against
        VTEX's services. Raises an exception if the credentials are invalid.

    configure(app, credentials): Configures a VTEX App instance with the provided API credentials.
        Updates the app configuration and marks it as configured.

Private Methods:
    _update_config(app, key, data): Updates the configuration of the given App instance
        with the provided data under the specified configuration key.

Raises:
    NoVTEXAppConfiguredException: If no VTEX App is configured for the given project UUID.
    MultipleVTEXAppsConfiguredException: If multiple configured VTEX Apps are found for the
        given project UUID, which is unexpected behavior.
    CredentialsValidationError: If the provided API credentials are found to be invalid during
        validation.

Data Classes:
    APICredentials: Data class that holds the structure for VTEX API credentials.

Exceptions:
    NoVTEXAppConfiguredException: Raised as an HTTP 404 Not Found if no VTEX App is configured
        for the given project UUID.
    MultipleVTEXAppsConfiguredException: Raised as an HTTP 400 Bad Request if multiple configured
        VTEX Apps are found for the given project UUID, which is unexpected behavior.
    CredentialsValidationError: Raised as an HTTP 400 Bad Request if provided API credentials
        are invalid.

"""
from dataclasses import dataclass
from django.core.exceptions import MultipleObjectsReturned

from marketplace.applications.models import App
from marketplace.services.vtex.private.products.service import (
    PrivateProductsService,
)
from marketplace.clients.vtex.client import VtexPrivateClient
from marketplace.services.vtex.exceptions import (
    CredentialsValidationError,
    NoVTEXAppConfiguredException,
    MultipleVTEXAppsConfiguredException,
)


@dataclass
class APICredentials:
    domain: str
    app_key: str
    app_token: str

    def to_dict(self):
        return {
            "domain": self.domain,
            "app_key": self.app_key,
            "app_token": self.app_token,
        }


class VtexService:
    def get_vtex_app_or_error(self, project_uuid):
        try:
            app_vtex = App.objects.get(
                code="vtex", project_uuid=str(project_uuid), configured=True
            )
            return app_vtex
        except App.DoesNotExist:
            raise NoVTEXAppConfiguredException()
        except MultipleObjectsReturned:
            raise MultipleVTEXAppsConfiguredException()

    def check_is_valid_credentials(self, credentials: APICredentials) -> bool:
        pvt_service = PrivateProductsService(
            VtexPrivateClient(
                credentials.app_key,
                credentials.app_token,
            )
        )
        if not pvt_service.validate_private_credentials(credentials.domain):
            raise CredentialsValidationError()

        return True

    def configure(self, app, credentials: APICredentials) -> App:
        updated_app = self._update_config(
            app, key="api_credentials", data=credentials.to_dict()
        )
        updated_app.configured = True
        updated_app.save()
        return updated_app

    # ================================
    # Private Methods
    # ================================

    def _update_config(self, app, key, data):
        app.config[key] = data
        return app
