import json
from unittest.mock import MagicMock

from django.test import TestCase

from marketplace.core.types.channels.facebook.usecases.search_products import (
    FacebookSearchProductsUseCase,
)


class FacebookSearchProductsUseCaseTest(TestCase):
    """Unit tests for FacebookSearchProductsUseCase."""

    def setUp(self) -> None:
        # Mock for FacebookService (only the method used by the use case)
        self.mock_service = MagicMock()
        self.mock_service.get_product_by_catalog_id.return_value = {"data": "ok"}

        # Instance of the use case with mocked service
        self.usecase = FacebookSearchProductsUseCase(service=self.mock_service)

    # ------------------------------------------------------------------ #
    # Helpers                                                             #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _service_call_kwargs(mock_service):
        """Return the kwargs of the latest get_product_by_catalog_id call."""
        return mock_service.get_product_by_catalog_id.call_args.kwargs

    # ------------------------------------------------------------------ #
    # Tests                                                              #
    # ------------------------------------------------------------------ #
    def test_execute_calls_service_with_correct_args(self):
        """execute() must build params and forward them to the service."""
        result = self.usecase.execute(
            catalog_id="123",
            product_ids=["SKU1", "SKU2"],
            fields=["id", "name"],
            summary=True,
            limit=50,
        )

        # Result propagated?
        self.assertEqual(result, {"data": "ok"})

        # Service called once
        self.mock_service.get_product_by_catalog_id.assert_called_once()

        # Validate kwargs mapping
        kwargs = self._service_call_kwargs(self.mock_service)
        self.assertEqual(kwargs["catalog_id"], "123")
        self.assertTrue(kwargs["summary"])
        self.assertEqual(kwargs["limit"], 50)

        # Fields must contain retailer_id in a CSV string
        self.assertEqual(kwargs["fields_str"], "id,name,retailer_id")

        # Filter must be a valid JSON with each SKU in an AND block
        filter_dict = json.loads(kwargs["filter_str"])
        self.assertEqual(len(filter_dict["or"]), 2)
        self.assertEqual(
            filter_dict["or"][0]["and"][0]["retailer_id"]["i_contains"], "SKU1"
        )

    def test_prepare_fields_appends_retailer_id(self):
        """_prepare_fields() should append retailer_id when missing."""
        csv = self.usecase._prepare_fields(["id", "name"])
        self.assertEqual(csv, "id,name,retailer_id")

    def test_prepare_fields_avoids_duplicate_retailer_id(self):
        """_prepare_fields() should not duplicate retailer_id."""
        csv = self.usecase._prepare_fields(["id", "retailer_id"])
        self.assertEqual(csv, "id,retailer_id")

    def test_build_filter_generates_expected_structure(self):
        """_build_filter() should create correct JSON structure."""
        json_str = self.usecase._build_filter(["ABC"])
        data = json.loads(json_str)

        self.assertIn("or", data)
        self.assertEqual(len(data["or"]), 1)

        and_block = data["or"][0]["and"]
        self.assertEqual(and_block[0]["retailer_id"]["i_contains"], "ABC")
        self.assertEqual(and_block[1]["availability"]["i_contains"], "in stock")
        self.assertEqual(and_block[2]["visibility"]["i_contains"], "published")
