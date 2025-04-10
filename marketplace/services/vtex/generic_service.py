"""
Service for managing VTEX App instances within a project.
"""

import logging

from typing import Optional, List

from dataclasses import dataclass

from marketplace.applications.models import App
from marketplace.core.types.ecommerce.vtex.usecases.sync_all_products import (
    SyncAllProductsUseCase,
)
from marketplace.core.types.ecommerce.vtex.usecases.sync_product_by_webhook import (
    SyncProductByWebhookUseCase,
)
from marketplace.services.vtex.private.products.service import (
    PrivateProductsService,
)
from marketplace.clients.vtex.client import VtexPrivateClient
from marketplace.services.vtex.exceptions import (
    CredentialsValidationError,
)
from marketplace.services.facebook.service import (
    FacebookService,
)
from marketplace.clients.facebook.client import FacebookClient

from marketplace.wpp_products.models import Catalog
from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.app_manager import AppVtexManager


logger = logging.getLogger(__name__)


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


class VtexServiceBase:
    fb_service_class = FacebookService
    fb_client_class = FacebookClient

    def __init__(self, *args, **kwargs):
        self._pvt_service = None
        self._fb_service = None
        self.product_manager = ProductFacebookManager()
        self.app_manager = AppVtexManager()

    def fb_service(self, app: App) -> FacebookService:  # pragma: no cover
        access_token = app.apptype.get_system_access_token(app)
        if not self._fb_service:
            self._fb_service = self.fb_service_class(self.fb_client_class(access_token))
        return self._fb_service

    def get_private_service(
        self, app_key, app_token
    ) -> PrivateProductsService:  # pragma nocover
        if not self._pvt_service:
            client = VtexPrivateClient(app_key, app_token)
            self._pvt_service = PrivateProductsService(client)
        return self._pvt_service

    def check_is_valid_credentials(self, credentials: APICredentials) -> bool:
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )
        if not pvt_service.validate_private_credentials(credentials.domain):
            raise CredentialsValidationError()

        return True

    def configure(
        self, app, credentials: APICredentials, wpp_cloud_uuid, store_domain
    ) -> App:
        app.config["api_credentials"] = credentials.to_dict()
        app.config["wpp_cloud_uuid"] = wpp_cloud_uuid
        app.config["initial_sync_completed"] = False
        app.config["title"] = credentials.domain
        app.config["connected_catalog"] = False
        app.config["rules"] = [
            "exclude_alcoholic_drinks",
            "calculate_by_weight",
            "currency_pt_br",
            "unifies_id_with_seller",
        ]
        app.config["store_domain"] = store_domain
        app.configured = True
        app.save()
        return app

    def get_vtex_credentials_or_raise(self, app: App) -> APICredentials:
        domain = app.config["api_credentials"]["domain"]
        app_key = app.config["api_credentials"]["app_key"]
        app_token = app.config["api_credentials"]["app_token"]
        if not domain or not app_key or not app_token:
            raise CredentialsValidationError()

        return APICredentials(
            app_key=app_key,
            app_token=app_token,
            domain=domain,
        )

    def active_sellers(self, app) -> List:
        credentials = self.get_vtex_credentials_or_raise(app)
        pvt_service = self.get_private_service(
            app_key=credentials.app_key, app_token=credentials.app_token
        )
        return pvt_service.list_active_sellers(credentials.domain)

    def synchronized_sellers(
        self, app: App, sellers_id: List = None, sync_all_sellers: bool = False
    ):
        try:
            sync_service = CatalogInsertionBySeller()
            sync_service.start_insertion_by_seller(
                vtex_app=app, sellers=sellers_id, sync_all_sellers=sync_all_sellers
            )
        except Exception as e:
            logger.error(
                f"Error on synchronized_sellers: {str(e)}",
                exc_info=True,
                stack_info=False,
                extra={
                    "App": str(app.uuid),
                    "Sellers": sellers_id,
                    "SyncAllSellers": sync_all_sellers,
                },
            )
            return False

        return True


class ProductInsertionService(VtexServiceBase):
    def first_product_insert(
        self,
        credentials: APICredentials,
        catalog: Catalog,
        sellers: Optional[List[str]] = None,
    ):
        """
        Handles the first product insert process using the SyncAllProductsUseCase.
        """
        # Initialize the private service with API credentials.
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )

        # Instantiate the sync use case with the private service.
        sync_use_case = SyncAllProductsUseCase(products_service=pvt_service)

        # Execute the use case with the required parameters.
        success = sync_use_case.execute(
            domain=credentials.domain,
            catalog=catalog,
            sellers=sellers,
            update_product=False,
            sync_specific_sellers=False,
        )
        print(f"First product sync completed for Catalog: {catalog.name}")
        self.app_manager.initial_sync_products_completed(catalog.vtex_app)
        return success


class ProductUpdateService(VtexServiceBase):
    def __init__(
        self,
        api_credentials: APICredentials,
        catalog: Catalog,
        skus_ids: list[str] = None,
        webhook: Optional[dict] = None,
        sellers_ids: list[str] = None,
        sellers_skus: list[str] = None,
    ):
        """
        Service for processing product updates via VTEX webhooks.
        """
        super().__init__()
        self.api_credentials = api_credentials
        self.catalog = catalog
        self.skus_ids = skus_ids
        self.app = self.catalog.app
        self.webhook = webhook
        self.sellers_ids = sellers_ids if sellers_ids else []
        self.sellers_skus = sellers_skus if sellers_skus else []
        self.product_manager = ProductFacebookManager()

    def process_batch_sync(self):
        """
        Processes product updates for the new batch synchronization method.
        """
        # Initialize private service
        pvt_service = self.get_private_service(
            self.api_credentials.app_key, self.api_credentials.app_token
        )

        # Create and execute the webhook sync use case
        sync_use_case = SyncProductByWebhookUseCase(products_service=pvt_service)

        # Execute the use case with the required parameters
        all_success = sync_use_case.execute(
            domain=self.api_credentials.domain,
            sellers_skus=self.sellers_skus,
            catalog=self.catalog,
        )

        if not all_success:
            raise Exception(
                f"Error saving batch products in database for Catalog: {self.catalog.facebook_catalog_id}"
            )

        return all_success

    def _get_sellers_ids(self, service):
        seller_id = extract_sellers_ids(self.webhook)
        if seller_id:
            return [seller_id]

        all_active_sellers = service.list_all_actives_sellers(
            self.api_credentials.domain
        )
        print("Seller not found, return all actives sellers")
        return all_active_sellers


def extract_sellers_ids(webhook):
    seller_an = webhook.get("An")
    seller_chain = webhook.get("SellerChain")

    if seller_chain and seller_an:
        return seller_chain

    if seller_an and not seller_chain:
        return seller_an

    return None


class CatalogProductInsertion:
    @classmethod
    def first_product_insert_with_catalog(
        cls, vtex_app: App, catalog_id: str, sellers: Optional[List[str]] = None
    ):
        """Inserts the first product with the given catalog."""
        wpp_cloud_uuid = cls._get_wpp_cloud_uuid(vtex_app)
        credentials = cls._get_credentials(vtex_app)
        wpp_cloud = cls._get_wpp_cloud(wpp_cloud_uuid)

        catalog = cls._get_or_sync_catalog(wpp_cloud, catalog_id)
        cls._update_app_connected_catalog_flag(vtex_app)
        cls._link_catalog_to_vtex_app_if_needed(catalog, vtex_app)

        cls._send_insert_task(credentials, catalog, sellers)

    @staticmethod
    def _get_wpp_cloud_uuid(vtex_app) -> str:
        """Retrieves WPP Cloud UUID from VTEX app config."""
        wpp_cloud_uuid = vtex_app.config.get("wpp_cloud_uuid")
        if not wpp_cloud_uuid:
            raise ValueError(
                "The VTEX app does not have the WPP Cloud UUID in its configuration."
            )
        return wpp_cloud_uuid

    @staticmethod
    def _get_credentials(vtex_app) -> dict:
        """Extracts API credentials from VTEX app config."""
        api_credentials = vtex_app.config.get("api_credentials", {})
        if not all(
            key in api_credentials for key in ["app_key", "app_token", "domain"]
        ):
            raise ValueError("Missing one or more API credentials.")
        return api_credentials

    @staticmethod
    def _get_wpp_cloud(wpp_cloud_uuid) -> App:
        """Fetches the WPP Cloud app based on UUID."""
        try:
            return App.objects.get(uuid=wpp_cloud_uuid)
        except App.DoesNotExist:
            raise ValueError(
                f"The cloud app {wpp_cloud_uuid} linked to the VTEX app does not exist."
            )

    @classmethod
    def _get_or_sync_catalog(cls, wpp_cloud, catalog_id) -> Catalog:
        from marketplace.wpp_products.tasks import FacebookCatalogSyncService

        """Attempts to find the catalog, syncs if not found, and tries again."""
        catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
        if not catalog:
            print(
                f"Catalog {catalog_id} not found for cloud app: {wpp_cloud.uuid}. Starting catalog synchronization."
            )
            sync_service = FacebookCatalogSyncService(wpp_cloud)
            sync_service.sync_catalogs()
            catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
            if not catalog:
                raise ValueError(
                    f"Catalog {catalog_id} not found for cloud app: {wpp_cloud.uuid} after synchronization."
                )
        return catalog

    @staticmethod
    def _link_catalog_to_vtex_app_if_needed(catalog, vtex_app) -> None:
        from django.contrib.auth import get_user_model

        """Links the catalog to the VTEX app if not already linked."""
        if not catalog.vtex_app:
            User = get_user_model()
            catalog.vtex_app = vtex_app
            catalog.modified_by = User.objects.get_admin_user()
            catalog.save()
            print(
                f"Catalog {catalog.name} successfully linked to VTEX app: {vtex_app.uuid}."
            )

    @staticmethod
    def _update_app_connected_catalog_flag(app) -> None:  # Vtex app
        """Change connected catalog status"""
        connected_catalog = app.config.get("connected_catalog", None)
        if connected_catalog is not True:
            app.config["connected_catalog"] = True
            app.save()
            print("Changed connected_catalog to True")

    @staticmethod
    def _send_insert_task(
        credentials, catalog, sellers: Optional[List[str]] = None
    ) -> None:
        from marketplace.celery import app as celery_app

        """Sends the insert task to the task queue."""
        celery_app.send_task(
            name="task_insert_vtex_products",
            kwargs={
                "credentials": credentials,
                "catalog_uuid": str(catalog.uuid),
                "sellers": sellers,
            },
            queue="product_first_synchronization",
        )
        print(
            f"Catalog: {catalog.name} was sent successfully sent to task_insert_vtex_products"
        )


class ProductInsertionBySellerService(VtexServiceBase):  # pragma: no cover
    """
    Service for inserting products by seller.

    This service fetches and processes products for specific sellers using the
    SyncAllProductsUseCase.
    """

    def insertion_products_by_seller(
        self,
        credentials: APICredentials,
        catalog: Catalog,
        sellers: List[str],
        sync_all_sellers: bool = False,
    ):
        """
        Fetches and processes products from specific sellers for insertion.

        Args:
            credentials: API credentials for accessing the VTEX platform.
            catalog: The catalog associated with the products.
            sellers: List of seller IDs to fetch products for.

        Returns:
            True if the sync was successful, otherwise raises an exception or returns False.
        """
        if not sellers and not sync_all_sellers:
            raise ValueError("'sellers' or 'sync_all_sellers' is required")

        # Initialize the private service.
        pvt_service = self.get_private_service(
            credentials.app_key, credentials.app_token
        )

        # Instantiate the sync use case with the private service.
        sync_use_case = SyncAllProductsUseCase(products_service=pvt_service)
        # Execute the use case with update flags enabled for seller-specific sync.
        success = sync_use_case.execute(
            domain=credentials.domain,
            catalog=catalog,
            sellers=sellers,
            update_product=True,
            sync_specific_sellers=True,
            sync_all_sellers=sync_all_sellers,
        )

        logger.info(f"Finished synchronizing products for specific sellers: {sellers}.")

        return success


class CatalogInsertionBySeller:  # pragma: no cover
    @classmethod
    def start_insertion_by_seller(
        cls, vtex_app: App, sellers: List[str] = None, sync_all_sellers: bool = False
    ):
        """
        Starts the insertion process for products by seller.

        Args:
            vtex_app: The VTEX app instance
            sellers: Optional list of seller IDs to synchronize
            sync_all_sellers: Flag to synchronize all active sellers

        Raises:
            ValueError: If required parameters are missing or validation fails
        """
        if not sellers and not sync_all_sellers:
            raise ValueError(
                "Either 'sellers' list or 'sync_all_sellers' must be provided."
            )

        wpp_cloud_uuid = cls._get_wpp_cloud_uuid(vtex_app)
        credentials = cls._get_credentials(vtex_app)
        wpp_cloud = cls._get_wpp_cloud(wpp_cloud_uuid)

        catalog = cls._validate_link_apps(wpp_cloud, vtex_app)

        cls._validate_connected_catalog_flag(vtex_app)
        cls._send_task(credentials, catalog, sellers, sync_all_sellers)

    @staticmethod
    def _get_wpp_cloud_uuid(vtex_app) -> str:
        """Retrieves WPP Cloud UUID from VTEX app config."""
        wpp_cloud_uuid = vtex_app.config.get("wpp_cloud_uuid")
        if not wpp_cloud_uuid:
            raise ValueError(
                "The VTEX app does not have the WPP Cloud UUID in its configuration."
            )
        return wpp_cloud_uuid

    @staticmethod
    def _get_credentials(vtex_app) -> dict:
        """Extracts API credentials from VTEX app config."""
        api_credentials = vtex_app.config.get("api_credentials", {})
        if not all(
            key in api_credentials for key in ["app_key", "app_token", "domain"]
        ):
            raise ValueError("Missing one or more API credentials.")
        return api_credentials

    @staticmethod
    def _get_wpp_cloud(wpp_cloud_uuid) -> App:
        """Fetches the WPP Cloud app based on UUID."""
        try:
            app = App.objects.get(uuid=wpp_cloud_uuid, code="wpp-cloud")
            if app.flow_object_uuid is None:
                print(f"Alert: App: {app.uuid} has the flow_object_uuid None field")
            return app
        except App.DoesNotExist:
            raise ValueError(
                f"The cloud app {wpp_cloud_uuid} linked to the VTEX app does not exist."
            )

    @classmethod
    def _validate_link_apps(cls, wpp_cloud, vtex_app) -> Catalog:
        """Checks for linked catalogs."""
        vtex_catalog = vtex_app.vtex_catalogs.first()

        if not vtex_catalog:
            raise ValueError(
                f"There must be a catalog linked to the vtex app {str(vtex_app.uuid)}"
            )

        catalog = wpp_cloud.catalogs.filter(
            facebook_catalog_id=vtex_catalog.facebook_catalog_id
        ).first()
        if not catalog:
            raise ValueError(
                f"Catalog {vtex_catalog.catalog_id} not found for cloud app: {wpp_cloud.uuid}."
            )

        print("validate_link_apps - Ok")
        return catalog

    @staticmethod
    def _validate_connected_catalog_flag(vtex_app) -> None:
        """Connected catalog status"""
        connected_catalog = vtex_app.config.get("connected_catalog", None)
        if connected_catalog is not True:
            raise ValueError(
                f"Change connected_catalog to True. actual is:{connected_catalog}"
            )

        print("validate_connected_catalog_flag - Ok")

    @staticmethod
    def _send_task(
        credentials,
        catalog,
        sellers: Optional[List[str]] = None,
        sync_all_sellers: bool = False,
    ) -> None:
        from marketplace.celery import app as celery_app

        """Sends the insert task to the task queue."""
        celery_app.send_task(
            name="task_insert_vtex_products_by_sellers",
            kwargs={
                "credentials": credentials,
                "catalog_uuid": str(catalog.uuid),
                "sellers": sellers,
                "sync_all_sellers": sync_all_sellers,
            },
            queue="product_first_synchronization",
        )
        print(
            f"Catalog: {catalog.name} was sent successfully sent to task_insert_vtex_products_by_sellers"
        )
