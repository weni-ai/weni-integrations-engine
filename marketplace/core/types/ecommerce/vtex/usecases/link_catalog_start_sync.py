import logging

from marketplace.applications.models import App

from typing import TypedDict

logger = logging.getLogger(__name__)


class LinkCatalogAndStartSyncUseCase:
    """
    Use case for linking a catalog to a VTEX app and triggering product synchronization.

    This use case performs the following steps:
      - Retrieve necessary credentials and cloud information from the VTEX app.
      - Link the provided catalog to the VTEX app if it is not already linked.
      - Dispatch the task to synchronize products from VTEX.
    """

    class CatalogSetupData(TypedDict):
        domain: str
        store_domain: str
        app_key: str
        app_token: str
        wpp_cloud_uuid: str

    def __init__(self, vtex_app: App, catalog_product_insertion=None):
        self.vtex_app = vtex_app

        if catalog_product_insertion is None:
            # TODO: Fix circular import error in the future
            from marketplace.services.vtex.generic_service import (
                CatalogProductInsertion,
            )

            self.catalog_product_insertion = CatalogProductInsertion
        else:
            self.catalog_product_insertion = catalog_product_insertion

    def configure_catalog(self, data: CatalogSetupData) -> None:
        """
        Setup vtex_app configs from linking catalog.

        Args:
            data: Mandatory data from linking catalog.

        Returns:
            None.
        """
        self.vtex_app.config["api_credentials"] = {
            "app_key": data.get("app_key"),
            "app_token": data.get("app_token"),
            "domain": data.get("domain"),
        }
        self.vtex_app.config["wpp_cloud_uuid"] = data.get("wpp_cloud_uuid")
        self.vtex_app.config["store_domain"] = data.get("store_domain")
        self.vtex_app.config["vtex_account"] = data.get("domain")
        self.vtex_app.config["rules"] = [
            "exclude_alcoholic_drinks",
            "calculate_by_weight",
            "currency_pt_br",
            "unifies_id_with_seller",
        ]
        self.vtex_app.save()

    def link_catalog(self, catalog_id: str) -> bool:
        """
        Execute the catalog linking and product synchronization process.

        Args:
            catalog_id: The catalog identifier provided from Meta.

        Returns:
            True if the task was dispatched successfully, False otherwise.
        """
        try:
            self.catalog_product_insertion.first_product_insert_with_catalog(
                vtex_app=self.vtex_app, catalog_id=catalog_id
            )
            return True
        except Exception as e:
            logger.error(f"Error linking catalog and syncing products: {str(e)}")
            return False
