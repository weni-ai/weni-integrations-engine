import logging

from typing import Optional, List

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog


logger = logging.getLogger(__name__)


class CatalogProductInsertion:
    @classmethod
    def first_product_insert_with_catalog(
        cls,
        vtex_app: App,
        catalog_id: str,
        sellers: Optional[List[str]] = None,
        sales_channel: Optional[list[str]] = None,
    ):
        """Inserts the first product with the given catalog."""
        wpp_cloud_uuid = cls._get_wpp_cloud_uuid(vtex_app)
        credentials = cls._get_credentials(vtex_app)
        wpp_cloud = cls._get_wpp_cloud(wpp_cloud_uuid)

        catalog = cls._get_or_sync_catalog(wpp_cloud, catalog_id)
        cls._update_app_connected_catalog_flag(vtex_app)
        cls._link_catalog_to_vtex_app_if_needed(catalog, vtex_app)

        cls._send_insert_task(credentials, catalog, sellers, sales_channel)

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
        if api_credentials.get("use_io_proxy"):
            if "domain" not in api_credentials:
                raise ValueError("Missing domain in IO proxy credentials.")
            return api_credentials

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

        catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
        if not catalog:
            logger.info(
                f"Catalog {catalog_id} not found for cloud app: {wpp_cloud.uuid}. "
                f"Starting catalog synchronization."
            )
            sync_service = FacebookCatalogSyncService(wpp_cloud)
            sync_service.sync_catalogs()
            catalog = wpp_cloud.catalogs.filter(facebook_catalog_id=catalog_id).first()
            if not catalog:
                raise ValueError(
                    f"Catalog {catalog_id} not found for cloud app: "
                    f"{wpp_cloud.uuid} after synchronization."
                )
        return catalog

    @staticmethod
    def _link_catalog_to_vtex_app_if_needed(catalog, vtex_app) -> None:
        from django.contrib.auth import get_user_model

        if not catalog.vtex_app:
            User = get_user_model()
            catalog.vtex_app = vtex_app
            catalog.modified_by = User.objects.get_admin_user()
            catalog.save()
            logger.info(f"Catalog {catalog.name} linked to VTEX app: {vtex_app.uuid}.")

    @staticmethod
    def _update_app_connected_catalog_flag(app) -> None:
        connected_catalog = app.config.get("connected_catalog", None)
        if connected_catalog is not True:
            app.config["connected_catalog"] = True
            app.save()

    @staticmethod
    def _send_insert_task(
        credentials,
        catalog,
        sellers: Optional[List[str]] = None,
        sales_channel: Optional[list[str]] = None,
    ) -> None:
        from marketplace.celery import app as celery_app

        celery_app.send_task(
            name="task_insert_vtex_products",
            kwargs={
                "credentials": credentials,
                "catalog_uuid": str(catalog.uuid),
                "sellers": sellers,
                "sales_channel": sales_channel,
            },
            queue="product_first_synchronization",
        )
        logger.info(f"Catalog: {catalog.name} sent to task_insert_vtex_products")


class CatalogInsertionBySeller:  # pragma: no cover
    @classmethod
    def start_insertion_by_seller(
        cls,
        vtex_app: App,
        sellers: List[str] = None,
        sync_all_sellers: bool = False,
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
        wpp_cloud_uuid = vtex_app.config.get("wpp_cloud_uuid")
        if not wpp_cloud_uuid:
            raise ValueError(
                "The VTEX app does not have the WPP Cloud UUID in its configuration."
            )
        return wpp_cloud_uuid

    @staticmethod
    def _get_credentials(vtex_app) -> dict:
        api_credentials = vtex_app.config.get("api_credentials", {})
        if api_credentials.get("use_io_proxy"):
            if "domain" not in api_credentials:
                raise ValueError("Missing domain in IO proxy credentials.")
            return api_credentials

        if not all(
            key in api_credentials for key in ["app_key", "app_token", "domain"]
        ):
            raise ValueError("Missing one or more API credentials.")
        return api_credentials

    @staticmethod
    def _get_wpp_cloud(wpp_cloud_uuid) -> App:
        try:
            app = App.objects.get(uuid=wpp_cloud_uuid, code="wpp-cloud")
            if app.flow_object_uuid is None:
                logger.warning(f"App: {app.uuid} has flow_object_uuid None")
            return app
        except App.DoesNotExist:
            raise ValueError(
                f"The cloud app {wpp_cloud_uuid} linked to the VTEX app does not exist."
            )

    @classmethod
    def _validate_link_apps(cls, wpp_cloud, vtex_app) -> Catalog:
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
                f"Catalog {vtex_catalog.catalog_id} not found "
                f"for cloud app: {wpp_cloud.uuid}."
            )

        return catalog

    @staticmethod
    def _validate_connected_catalog_flag(vtex_app) -> None:
        connected_catalog = vtex_app.config.get("connected_catalog", None)
        if connected_catalog is not True:
            raise ValueError(
                f"connected_catalog must be True, got: {connected_catalog}"
            )

    @staticmethod
    def _send_task(
        credentials,
        catalog,
        sellers: Optional[List[str]] = None,
        sync_all_sellers: bool = False,
    ) -> None:
        from marketplace.celery import app as celery_app

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
        logger.info(
            f"Catalog: {catalog.name} sent to task_insert_vtex_products_by_sellers"
        )
