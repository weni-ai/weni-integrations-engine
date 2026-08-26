import logging

from typing import Optional

from rest_framework.exceptions import NotFound

from marketplace.applications.models import App
from marketplace.core.types.ecommerce.dtos.upload_inline_products_dto import (
    UploadInlineProductsDTO,
)
from marketplace.services.product.product_facebook_manage import ProductFacebookManager
from marketplace.services.vtex.utils.enums import ProductPriority
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.wpp_products.utils import UploadManager


logger = logging.getLogger(__name__)


class UploadInlineProductsUseCase:
    """
    Persists pre-formatted inline products and triggers their upload to Meta.

    Unlike the inline sync flow, products arrive already formatted by the caller (optionally
    edited), so no VTEX lookup is performed. Credentials and catalog resolution mirror the
    inline flow: the VTEX app is resolved from the project UUID carried by the JWT and its
    linked catalog drives the Meta upload (using the wpp-cloud system token under the hood).
    """

    def __init__(
        self,
        product_manager: Optional[ProductFacebookManager] = None,
        priority: int = ProductPriority.ON_DEMAND,
    ) -> None:
        self.priority = priority
        self.product_manager = product_manager or ProductFacebookManager(
            priority=priority
        )

    def execute(self, dto: UploadInlineProductsDTO, project_uuid: str) -> int:
        """
        Save the products and dispatch the asynchronous upload.

        Returns:
            The number of products queued for upload.
        """
        vtex_app = self._get_vtex_app(project_uuid)
        catalog = vtex_app.vtex_catalogs.first()
        if not catalog:
            raise NotFound(
                "No catalog is linked to the VTEX app for the provided project UUID."
            )

        products_dto = [self._build_product_dto(product) for product in dto.products]

        logger.info(
            f"Uploading {len(products_dto)} inline products for "
            f"project={project_uuid} catalog={catalog.name}"
        )
        self.product_manager.bulk_save_initial_product_data(products_dto, catalog)
        UploadManager.check_and_start_upload(str(vtex_app.uuid), priority=self.priority)

        return len(products_dto)

    def _get_vtex_app(self, project_uuid: str) -> App:
        try:
            return App.objects.get(project_uuid=project_uuid, code="vtex")
        except App.DoesNotExist:
            raise NotFound(
                "A vtex-app integration was not found for the provided project UUID."
            )

    @staticmethod
    def _build_product_dto(product: dict) -> FacebookProductDTO:
        return FacebookProductDTO(
            id=product["id"],
            title=product["title"],
            description=product.get("description", ""),
            availability=product["availability"],
            status=product["status"],
            condition=product["condition"],
            price=product.get("price", ""),
            link=product["link"],
            image_link=product["image_link"],
            brand=product.get("brand", ""),
            sale_price=product.get("sale_price", ""),
            additional_image_link=product.get("additional_image_link", ""),
            rich_text_description=product.get("rich_text_description", ""),
            product_details={},
        )
