import logging

from rest_framework.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.services.vtex.catalog_insertion import (
    CatalogProductInsertion,
)


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
        self.catalog_product_insertion = (
            catalog_product_insertion or CatalogProductInsertion
        )

    def execute(self, vtex_app: App, catalog_id: str, sales_channel: list[str] = None):
        """
        Execute the catalog linking and product synchronization process.

        Args:
            vtex_app: The VTEX app instance.
            catalog_id: The catalog identifier provided from Meta.
            sales_channel: Optional sales channel list.

        Raises:
            ValidationError: If catalog is not found or configuration is invalid.
        """
        try:
            self.catalog_product_insertion.first_product_insert_with_catalog(
                vtex_app=vtex_app,
                catalog_id=catalog_id,
                sales_channel=sales_channel,
            )
        except ValueError as e:
            logger.error(
                f"Failed to link catalog {catalog_id} " f"for app {vtex_app.uuid}: {e}"
            )
            raise ValidationError(str(e))
