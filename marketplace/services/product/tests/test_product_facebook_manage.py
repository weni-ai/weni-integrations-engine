from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase

from marketplace.services.product.product_facebook_manage import (
    ProductFacebookManager,
)


class TestProductFacebookManager(SimpleTestCase):
    def test_constructor_defaults(self):
        manager = ProductFacebookManager()
        self.assertEqual(manager.batch_size, 10_000)
        self.assertEqual(manager.priority, 0)

    @patch("marketplace.services.product.product_facebook_manage.transaction")
    @patch("marketplace.services.product.product_facebook_manage.UploadProduct")
    def test_bulk_save_success_saves_and_removes_duplicates(
        self, mock_upload_product, mock_tx
    ):
        # Arrange atomic context manager
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = None
        mock_tx.atomic.return_value = cm  # type: ignore[attr-defined]

        dto1 = MagicMock()
        dto1.id = "p1"
        dto1.to_meta_payload.return_value = {"id": "p1"}
        dto2 = MagicMock()
        dto2.id = "p2"
        dto2.to_meta_payload.return_value = {"id": "p2"}

        catalog = MagicMock()
        catalog.name = "CAT"

        mock_upload_product.objects.bulk_create.return_value = None

        manager = ProductFacebookManager(batch_size=5, priority=7)

        # Act
        ok = manager.bulk_save_initial_product_data([dto1, dto2], catalog)

        # Assert
        self.assertTrue(ok)
        # Two UploadProduct(...) created with expected kwargs
        created_calls = [call.kwargs for call in mock_upload_product.call_args_list]
        self.assertEqual(
            created_calls,
            [
                {
                    "facebook_product_id": "p1",
                    "catalog": catalog,
                    "data": {"id": "p1"},
                    "status": "pending",
                    "priority": 7,
                },
                {
                    "facebook_product_id": "p2",
                    "catalog": catalog,
                    "data": {"id": "p2"},
                    "status": "pending",
                    "priority": 7,
                },
            ],
        )
        # bulk_create called with two new product instances and batch size
        args, kwargs = mock_upload_product.objects.bulk_create.call_args
        self.assertEqual(len(args[0]), 2)
        self.assertEqual(kwargs.get("batch_size"), 5)
        # remove_duplicates always called
        mock_upload_product.remove_duplicates.assert_called_once_with(catalog)

    @patch("marketplace.services.product.product_facebook_manage.transaction")
    @patch("marketplace.services.product.product_facebook_manage.UploadProduct")
    def test_bulk_save_exception_returns_false_and_still_deduplicates(
        self, mock_upload_product, mock_tx
    ):
        cm = MagicMock()
        cm.__enter__.return_value = None
        cm.__exit__.return_value = None
        mock_tx.atomic.return_value = cm  # type: ignore[attr-defined]

        dto = MagicMock()
        dto.id = "x1"
        dto.to_meta_payload.return_value = {"id": "x1"}
        catalog = MagicMock()

        mock_upload_product.objects.bulk_create.side_effect = Exception("boom")

        manager = ProductFacebookManager()
        ok = manager.bulk_save_initial_product_data([dto], catalog)

        self.assertFalse(ok)
        mock_upload_product.remove_duplicates.assert_called_once_with(catalog)
