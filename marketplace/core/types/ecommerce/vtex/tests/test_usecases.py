import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from unittest.mock import Mock, patch

from rest_framework.exceptions import NotFound

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog, UploadProduct
from marketplace.core.types.ecommerce.dtos.upload_inline_products_dto import (
    UploadInlineProductsDTO,
)
from marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand import (
    SyncOnDemandUseCase,
)
from marketplace.core.types.ecommerce.vtex.usecases.upload_inline_products import (
    UploadInlineProductsUseCase,
)
from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)
from marketplace.services.vtex.tests.fakes import VtexTestEnvironment
from marketplace.services.vtex.utils.enums import ProductPriority
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO


User = get_user_model()


class VtexIntegrationTest(TestCase):
    def setUp(self):
        self.project_uuid = uuid.uuid4()

        self.user = User.objects.create_superuser(
            email="admin@marketplace.ai", password="fake@pass#$"
        )

        self.vtex_app = App.objects.create(
            code="vtex",
            project_uuid=self.project_uuid,
            created_by=self.user,
            config={
                "operator_token": {
                    "app_key": "key123",
                    "app_token": "token123",
                    "domain": "vtex.com",
                }
            },
        )

    def test_get_integration_details_success(self):
        # Test if VTEX integration credentials are returned correctly
        result = VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(result["app_key"], "key123")
        self.assertEqual(result["app_token"], "token123")
        self.assertEqual(result["domain"], "https://vtex.com")

    def test_get_integration_details_not_found(self):
        # Test if the NotFound exception is raised when the App is not found
        invalid_uuid = uuid.uuid4()
        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(invalid_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "A vtex-app integration was not found for the provided project UUID.",
        )

    def test_ensure_https_with_http(self):
        # Test if ensure_https method correctly adds 'https://' to the domain
        domain = "vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, "https://vtex.com")

    def test_ensure_https_already_secure(self):
        # Test if ensure_https method does not modify domains that already start with 'https://'
        domain = "https://vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, domain)

    def test_ensure_https_empty(self):
        # Test if ensure_https method handles None and empty strings correctly
        result = VtexIntegration.ensure_https(None)
        self.assertIsNone(result)

        result = VtexIntegration.ensure_https("")
        self.assertEqual(result, "")

    def test_get_integration_details_operator_token_not_found(self):
        # Test whether the NotFound exception is raised when the operator_token is not found
        # Remove operator_token from App configuration
        self.vtex_app.config.pop("operator_token")
        self.vtex_app.save()

        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "The operator_token was not found for the provided project UUID.",
        )


class SyncOnDemandUseCaseTest(TestCase):
    def setUp(self):
        self.mock_celery_app = Mock()
        self.use_case = SyncOnDemandUseCase(celery_app=self.mock_celery_app)

        self.mock_catalog = Mock(spec=Catalog)
        self.mock_app = Mock(spec=App)
        self.mock_app.vtex_catalogs.first.return_value = self.mock_catalog
        self.mock_app.config = {"celery_queue_name": "test_queue"}
        self.mock_app.uuid = "fake-uuid"

    # TODO: Fix this test
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._get_vtex_app"
    # )
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._is_product_valid"
    # )
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._product_exists"
    # )
    # def test_execute_triggers_tasks_for_valid_products(
    #     self, mock_product_exists, mock_is_valid, mock_get_app
    # ):
    #     mock_get_app.return_value = self.mock_app
    #     mock_is_valid.return_value = True
    #     mock_product_exists.return_value = True

    #     data = {"seller": "seller1", "sku_ids": ["sku1", "sku2"]}
    #     project_uuid = "project-uuid"

    #     self.use_case.execute(data, project_uuid)

    #     self.assertEqual(self.mock_celery_app.send_task.call_count, 4)
    #     self.mock_celery_app.send_task.assert_any_call(
    #         "task_enqueue_webhook",
    #         kwargs={"app_uuid": "fake-uuid", "seller": "seller1", "sku_id": "sku1"},
    #         queue="test_queue",
    #         ignore_result=True,
    #     )
    #     self.mock_celery_app.send_task.assert_any_call(
    #         "task_dequeue_webhooks",
    #         kwargs={"app_uuid": "fake-uuid", "celery_queue": "test_queue"},
    #         queue="test_queue",
    #         ignore_result=True,
    #     )

    # TODO: Fix this test
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._get_vtex_app"
    # )
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._is_product_valid"
    # )
    # @patch(
    #     "marketplace.core.types.ecommerce.vtex.usecases.sync_on_demand.SyncOnDemandUseCase._product_exists"
    # )
    # def test_execute_does_not_trigger_tasks_for_invalid_products(
    #     self, mock_product_exists, mock_is_valid, mock_get_app
    # ):
    #     mock_get_app.return_value = self.mock_app
    #     mock_product_exists.side_effect = lambda sku_id, catalog: True
    #     mock_is_valid.side_effect = lambda sku_id, catalog: sku_id != "sku2"

    #     data = {"seller": "seller1", "sku_ids": ["sku1", "sku2"]}
    #     project_uuid = "project-uuid"

    #     self.use_case.execute(data, project_uuid)

    #     self.assertEqual(self.mock_celery_app.send_task.call_count, 2)
    #     self.mock_celery_app.send_task.assert_any_call(
    #         "task_enqueue_webhook",
    #         kwargs={"app_uuid": "fake-uuid", "seller": "seller1", "sku_id": "sku1"},
    #         queue="test_queue",
    #         ignore_result=True,
    #     )
    #     self.mock_celery_app.send_task.assert_any_call(
    #         "task_dequeue_webhooks",
    #         kwargs={"app_uuid": "fake-uuid", "celery_queue": "test_queue"},
    #         queue="test_queue",
    #         ignore_result=True,
    #     )

    @patch("marketplace.applications.models.App.objects.get")
    def test_get_vtex_app_returns_app(self, mock_get):
        mock_app = Mock()
        mock_get.return_value = mock_app

        result = self.use_case._get_vtex_app("some-uuid")

        mock_get.assert_called_once_with(project_uuid="some-uuid", code="vtex")
        self.assertEqual(result, mock_app)

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_is_product_valid_returns_true(self, mock_filter):
        mock_filter.return_value.exists.return_value = True

        result = self.use_case._is_product_valid("sku1", "mock_catalog")

        mock_filter.assert_called_once_with(
            sku_id="sku1", is_valid=True, catalog="mock_catalog"
        )
        self.assertTrue(result)

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_is_product_valid_returns_false(self, mock_filter):
        mock_filter.return_value.exists.return_value = False

        result = self.use_case._is_product_valid("sku2", "mock_catalog")

        mock_filter.assert_called_once_with(
            sku_id="sku2", is_valid=True, catalog="mock_catalog"
        )
        self.assertFalse(result)

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_product_exists_returns_true(self, mock_filter):
        mock_filter.return_value.exists.return_value = True

        result = self.use_case._product_exists("sku1", "mock_catalog")

        mock_filter.assert_called_once_with(sku_id="sku1", catalog="mock_catalog")
        self.assertTrue(result)

    @patch("marketplace.wpp_products.models.ProductValidation.objects.filter")
    def test_product_exists_returns_false(self, mock_filter):
        mock_filter.return_value.exists.return_value = False

        result = self.use_case._product_exists("sku2", "mock_catalog")

        mock_filter.assert_called_once_with(sku_id="sku2", catalog="mock_catalog")
        self.assertFalse(result)


UPLOAD_USECASE_PATH = (
    "marketplace.core.types.ecommerce.vtex.usecases.upload_inline_products"
)


class UploadInlineProductsUseCaseTest(TestCase):
    def setUp(self):
        self.project_uuid = "project-uuid"
        self.product = {
            "id": "1047#1",
            "title": "Laranja Bahia Importada - Saco (15Kg)",
            "description": "Laranja Bahia Importada - Saco (15Kg)",
            "availability": "in stock",
            "status": "active",
            "condition": "new",
            "price": "10.00 BRL",
            "link": "https://www.arado.com.br/laranja-bahia-importada-1/p?idsku=1047",
            "image_link": "https://arado.vteximg.com.br/arquivos/ids/158691/img.jpg",
            "brand": "Arado",
            "sale_price": "8.00 BRL",
            "additional_image_link": "",
            "rich_text_description": "",
        }
        self.dto = UploadInlineProductsDTO(products=[self.product])

        self.mock_product_manager = Mock()
        self.use_case = UploadInlineProductsUseCase(
            product_manager=self.mock_product_manager
        )

        self.mock_catalog = Mock(spec=Catalog)
        self.mock_catalog.name = "Test Catalog"
        self.mock_app = Mock(spec=App)
        self.mock_app.uuid = "vtex-app-uuid"
        self.mock_app.vtex_catalogs.first.return_value = self.mock_catalog

    def test_default_priority_is_on_demand(self):
        self.assertEqual(self.use_case.priority, ProductPriority.ON_DEMAND)

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    @patch("marketplace.applications.models.App.objects.get")
    def test_execute_saves_products_and_triggers_upload(
        self, mock_get, mock_check_upload
    ):
        mock_get.return_value = self.mock_app

        total = self.use_case.execute(self.dto, self.project_uuid)

        self.assertEqual(total, 1)
        mock_get.assert_called_once_with(project_uuid=self.project_uuid, code="vtex")

        self.mock_product_manager.bulk_save_initial_product_data.assert_called_once()
        (
            saved_products,
            saved_catalog,
        ) = self.mock_product_manager.bulk_save_initial_product_data.call_args.args
        self.assertEqual(saved_catalog, self.mock_catalog)
        self.assertEqual(len(saved_products), 1)
        self.assertIsInstance(saved_products[0], FacebookProductDTO)
        self.assertEqual(saved_products[0].id, "1047#1")

        mock_check_upload.assert_called_once_with(
            "vtex-app-uuid", priority=ProductPriority.ON_DEMAND
        )

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    @patch("marketplace.applications.models.App.objects.get")
    def test_execute_raises_not_found_when_vtex_app_missing(
        self, mock_get, mock_check_upload
    ):
        mock_get.side_effect = App.DoesNotExist

        with self.assertRaises(NotFound):
            self.use_case.execute(self.dto, self.project_uuid)

        self.mock_product_manager.bulk_save_initial_product_data.assert_not_called()
        mock_check_upload.assert_not_called()

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    @patch("marketplace.applications.models.App.objects.get")
    def test_execute_raises_not_found_when_no_catalog_linked(
        self, mock_get, mock_check_upload
    ):
        self.mock_app.vtex_catalogs.first.return_value = None
        mock_get.return_value = self.mock_app

        with self.assertRaises(NotFound):
            self.use_case.execute(self.dto, self.project_uuid)

        self.mock_product_manager.bulk_save_initial_product_data.assert_not_called()
        mock_check_upload.assert_not_called()

    def test_build_product_dto_maps_all_fields(self):
        dto = self.use_case._build_product_dto(self.product)

        self.assertEqual(dto.id, "1047#1")
        self.assertEqual(dto.title, self.product["title"])
        self.assertEqual(dto.price, "10.00 BRL")
        self.assertEqual(dto.sale_price, "8.00 BRL")
        self.assertEqual(dto.product_details, {})

    def test_build_product_dto_defaults_optional_fields(self):
        minimal_product = {
            "id": "55#1",
            "title": "Minimal",
            "availability": "in stock",
            "status": "active",
            "condition": "new",
            "price": "1.00 BRL",
            "link": "https://example.com/p",
            "image_link": "https://example.com/img.jpg",
        }

        dto = self.use_case._build_product_dto(minimal_product)

        self.assertEqual(dto.description, "")
        self.assertEqual(dto.brand, "")
        self.assertEqual(dto.sale_price, "")
        self.assertEqual(dto.additional_image_link, "")
        self.assertEqual(dto.rich_text_description, "")


class UploadInlineProductsUseCaseIntegrationTest(TestCase):
    """
    Exercises the full use case against the real database, persisting UploadProduct rows.

    Only the upload trigger (UploadManager -> redis/celery) is mocked, so the persistence
    path (ProductFacebookManager, payload filtering and dedup) runs for real.
    """

    def setUp(self):
        # Reuses the shared VTEX test environment (DB fixtures + fakes).
        self.env = VtexTestEnvironment.create(catalog_name="Integration Catalog")
        self.vtex_app = self.env.vtex_app
        self.catalog = self.env.catalog
        self.project_uuid = self.env.project_uuid

        self.product = {
            "id": "1047#1",
            "title": "Laranja Bahia Importada - Saco (15Kg)",
            "description": "Laranja Bahia Importada - Saco (15Kg)",
            "availability": "in stock",
            "status": "active",
            "condition": "new",
            "price": "10.00 BRL",
            "link": "https://www.arado.com.br/laranja-bahia-importada-1/p?idsku=1047",
            "image_link": "https://arado.vteximg.com.br/arquivos/ids/158691/img.jpg",
            "brand": "Arado",
            "sale_price": "8.00 BRL",
            "additional_image_link": "",
            "rich_text_description": "",
        }
        self.use_case = UploadInlineProductsUseCase()

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    def test_execute_persists_upload_products_and_triggers_upload(
        self, mock_check_upload
    ):
        dto = UploadInlineProductsDTO(products=[self.product])

        total = self.use_case.execute(dto, self.project_uuid)

        self.assertEqual(total, 1)
        mock_check_upload.assert_called_once_with(
            str(self.vtex_app.uuid), priority=ProductPriority.ON_DEMAND
        )

        uploads = UploadProduct.objects.filter(catalog=self.catalog)
        self.assertEqual(uploads.count(), 1)

        upload = uploads.first()
        self.assertEqual(upload.facebook_product_id, "1047#1")
        self.assertEqual(upload.status, "pending")
        self.assertEqual(upload.priority, ProductPriority.ON_DEMAND)
        self.assertEqual(upload.data["id"], "1047#1")
        self.assertEqual(upload.data["price"], "10.00 BRL")
        self.assertEqual(upload.data["sale_price"], "8.00 BRL")
        # Empty fields are stripped from the Meta payload
        self.assertNotIn("additional_image_link", upload.data)
        self.assertNotIn("rich_text_description", upload.data)

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    def test_execute_dedups_repeated_product_ids_keeping_latest(
        self, mock_check_upload
    ):
        edited_product = dict(self.product, price="12.00 BRL")
        dto = UploadInlineProductsDTO(products=[self.product, edited_product])

        self.use_case.execute(dto, self.project_uuid)

        uploads = UploadProduct.objects.filter(
            catalog=self.catalog, facebook_product_id="1047#1"
        )
        self.assertEqual(uploads.count(), 1)
        self.assertEqual(uploads.first().data["price"], "12.00 BRL")

    @patch(f"{UPLOAD_USECASE_PATH}.UploadManager.check_and_start_upload")
    def test_execute_raises_not_found_when_no_catalog_linked(self, mock_check_upload):
        self.catalog.delete()
        dto = UploadInlineProductsDTO(products=[self.product])

        with self.assertRaises(NotFound):
            self.use_case.execute(dto, self.project_uuid)

        self.assertEqual(UploadProduct.objects.count(), 0)
        mock_check_upload.assert_not_called()
