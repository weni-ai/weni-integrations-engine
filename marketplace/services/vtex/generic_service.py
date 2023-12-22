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
from datetime import datetime

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
from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.clients.facebook.client import FacebookClient
from marketplace.wpp_products.models import ProductFeed
from marketplace.wpp_products.models import Catalog
from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.exceptions import (
    UnexpectedFacebookApiResponseValidationError,
)
from marketplace.services.vtex.exceptions import FileNotSendValidationError


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
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        self._pvt_service = None
        self._fb_service = None
        self.product_manager = ProductFacebookManager()

    @property
    def fb_service(self) -> FacebookService:  # pragma: no cover
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class())
        return self._fb_service

    def get_private_service(
        self, app_key, app_token
    ) -> PrivateProductsService:  # pragma nocover
        if not self._pvt_service:
            client = VtexPrivateClient(app_key, app_token)
            self._pvt_service = PrivateProductsService(client)
        return self._pvt_service

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
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        if not pvt_service.validate_private_credentials(credentials.domain):
            raise CredentialsValidationError()

        return True

    def configure(self, app, credentials: APICredentials, wpp_cloud_uuid) -> App:
        app.config["api_credentials"] = credentials.to_dict()
        app.config["wpp_cloud_uuid"] = wpp_cloud_uuid
        app.config["initial_sync_completed"] = False
        app.config["rules"] = [
            "currency_pt_br",
            "calculate_by_weight",
            "exclude_alcoholic_drinks",
            "unifies_id_with_seller",
        ]
        app.configured = True
        app.save()
        return app

    def first_insert(self, credentials: APICredentials, catalog):
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        products = pvt_service.list_all_products(
            credentials.domain, catalog.vtex_app.config
        )
        products_csv = pvt_service.data_processor.products_to_csv(products)
        product_feed = self._send_products_to_facebook(products_csv, catalog)
        self.product_manager.save_products_on_database(products, catalog, product_feed)
        return True

    def _send_products_to_facebook(self, products_csv, catalog: Catalog):
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
        file_name = f"csv_vtex_products_{current_time}.csv"
        product_feed = self._create_product_feed(file_name, catalog)
        self._upload_product_feed(
            product_feed.facebook_feed_id,
            products_csv,
            file_name,
        )
        return product_feed

    def _create_product_feed(self, name, catalog: Catalog) -> ProductFeed:
        response = self.fb_service.create_product_feed(
            catalog.facebook_catalog_id, name
        )

        if "id" not in response:
            raise UnexpectedFacebookApiResponseValidationError()

        product_feed = ProductFeed.objects.create(
            facebook_feed_id=response["id"],
            name=name,
            catalog=catalog,
            created_by=catalog.created_by,
        )
        return product_feed

    def _upload_product_feed(self, product_feed_id, csv_file, file_name):
        response = self.fb_service.upload_product_feed(
            product_feed_id, csv_file, file_name, "text/csv"
        )
        if "id" not in response:
            raise FileNotSendValidationError()

        return True
