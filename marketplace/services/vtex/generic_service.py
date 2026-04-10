"""
Service for managing VTEX App instances within a project.
"""

import logging

from typing import Optional, List

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
from marketplace.clients.vtex.proxy_client import VtexProxyClient
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
from marketplace.services.vtex.dtos import APICredentials  # noqa: F401
from marketplace.services.vtex.catalog_insertion import (  # noqa: F401
    CatalogProductInsertion,
    CatalogInsertionBySeller,
)
from marketplace.services.vtex.utils.enums import ProductPriority


logger = logging.getLogger(__name__)


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

    def _create_vtex_client(self, credentials: APICredentials):
        if credentials.use_io_proxy:
            return VtexProxyClient(project_uuid=credentials.project_uuid)
        return VtexPrivateClient(credentials.app_key, credentials.app_token)

    def get_private_service_for_credentials(
        self, credentials: APICredentials
    ) -> PrivateProductsService:
        if not self._pvt_service:
            client = self._create_vtex_client(credentials)
            self._pvt_service = PrivateProductsService(client)
        return self._pvt_service

    def check_is_valid_credentials(self, credentials: APICredentials) -> bool:
        if credentials.use_io_proxy:
            return True

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
        api_credentials = app.config.get("api_credentials", {})
        domain = api_credentials.get("domain")
        if not domain:
            raise CredentialsValidationError()

        if api_credentials.get("use_io_proxy"):
            return APICredentials(
                domain=domain,
                use_io_proxy=True,
                project_uuid=api_credentials.get("project_uuid", str(app.project_uuid)),
            )

        app_key = api_credentials.get("app_key")
        app_token = api_credentials.get("app_token")
        if not app_key or not app_token:
            raise CredentialsValidationError()

        return APICredentials(
            app_key=app_key,
            app_token=app_token,
            domain=domain,
        )

    def active_sellers(self, app) -> List:
        credentials = self.get_vtex_credentials_or_raise(app)
        pvt_service = self.get_private_service_for_credentials(credentials)
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
        sales_channel: Optional[list[str]] = None,
    ):
        """
        Handles the first product insert process using the SyncAllProductsUseCase.
        """
        pvt_service = self.get_private_service_for_credentials(credentials)
        sync_use_case = SyncAllProductsUseCase(products_service=pvt_service)

        success = sync_use_case.execute(
            domain=credentials.domain,
            catalog=catalog,
            sellers=sellers,
            update_product=False,
            sync_specific_sellers=False,
            sales_channel=sales_channel,
        )
        print(f"First product sync completed for Catalog: {catalog.name}")
        self.app_manager.initial_sync_products_completed(catalog.vtex_app)
        return success


class ProductUpdateService(VtexServiceBase):
    """
    Service for processing product updates via VTEX webhooks.
    Handles legacy, async (priority 1), and inline (priority 2) batch processing.
    """

    def __init__(
        self,
        api_credentials: APICredentials,
        catalog: Catalog,
        skus_ids: list[str] = None,
        webhook: Optional[dict] = None,
        sellers_ids: list[str] = None,
        sellers_skus: list[str] = None,
        priority: int = ProductPriority.DEFAULT,
        sales_channel: Optional[list[str]] = None,
    ):
        """
        Args:
            api_credentials (APICredentials): VTEX API credentials.
            catalog (Catalog): Product catalog instance.
            skus_ids (list[str], optional): List of SKUs for update.
            webhook (dict, optional): Webhook data.
            sellers_ids (list[str], optional): List of seller IDs.
            sellers_skus (list[str], optional): List of seller#sku identifiers.
            priority (int): Type of synchronization (0=legacy, 1=async, 2=inline).
            sales_channel (list[str], optional): Sales channel.
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
        self.priority = priority
        self.sales_channel = sales_channel

    def process_batch_sync(self):
        """
        Processes product updates for the batch synchronization method.

        For priorities 0 and 1 (default/async):
            - Returns True if all products were successfully saved, otherwise raises Exception.
        For priority 2 (inline/API_ONLY):
            - Returns a list of processed products (which may be empty).

        Returns:
            Union[bool, list]:
                - True for successful batch save (priority 0/1).
                - List of processed products for inline sync (priority 2).
                - On error: [] for priority 2, False for other priorities.

        Raises:
            Exception: If the batch process fails for priorities 0 or 1.
        """
        pvt_service = self.get_private_service_for_credentials(self.api_credentials)
        sync_use_case = SyncProductByWebhookUseCase(products_service=pvt_service)

        try:
            processed = sync_use_case.execute(
                domain=self.api_credentials.domain,
                sellers_skus=self.sellers_skus,
                catalog=self.catalog,
                priority=self.priority,
                sales_channel=self.sales_channel,
            )
            if self.priority == ProductPriority.API_ONLY:
                # For inline/API_ONLY, return the processed list (may be empty)
                return processed if isinstance(processed, list) else []
            # For batch/async, require True as success
            if not processed:
                raise Exception(
                    f"Error saving batch products in database for Catalog: {self.catalog.facebook_catalog_id}"
                )
            return processed  # Should be True
        except Exception as exc:
            logger.error(f"Error in ProductUpdateService.process_batch_sync: {exc}")
            # On error, return [] for priority API_ONLY, False for others
            return [] if self.priority == ProductPriority.API_ONLY else False

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
        sales_channel: Optional[list[str]] = None,
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

        pvt_service = self.get_private_service_for_credentials(credentials)
        sync_use_case = SyncAllProductsUseCase(products_service=pvt_service)
        success = sync_use_case.execute(
            domain=credentials.domain,
            catalog=catalog,
            sellers=sellers,
            update_product=True,
            sync_specific_sellers=True,
            sync_all_sellers=sync_all_sellers,
            sales_channel=sales_channel,
        )

        logger.info(f"Finished synchronizing products for specific sellers: {sellers}.")

        return success
