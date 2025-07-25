import logging

from marketplace.applications.models import App


logger = logging.getLogger(__name__)


class LinkCatalogAndStartSyncUseCase:
    """
    Use case for linking a catalog to a VTEX app and triggering product synchronization.

    This use case performs the following steps:
      - Retrieve necessary credentials and cloud information from the VTEX app.
      - Link the provided catalog to the VTEX app if it is not already linked.
      - Dispatch the task to synchronize products from VTEX.
    """

    def __init__(self, catalog_product_insertion=None):
        if catalog_product_insertion is None:
            # TODO: Fix circular import error in the future
            from marketplace.services.vtex.generic_service import (
                CatalogProductInsertion,
            )

            self.catalog_product_insertion = CatalogProductInsertion
        else:
            self.catalog_product_insertion = catalog_product_insertion

    def execute(
        self, vtex_app: App, catalog_id: str, sales_channel: list[str] = None
    ) -> bool:
        """
        Execute the catalog linking and product synchronization process.

        Args:
            vtex_app: The VTEX app instance.
            catalog_id: The catalog identifier provided from Meta.

        Returns:
            True if the task was dispatched successfully, False otherwise.
        """
        try:
            self.catalog_product_insertion.first_product_insert_with_catalog(
                vtex_app=vtex_app, catalog_id=catalog_id, sales_channel=sales_channel
            )
            return True
        except Exception as e:
            logger.error(f"Error linking catalog and syncing products: {str(e)}")
            return False
