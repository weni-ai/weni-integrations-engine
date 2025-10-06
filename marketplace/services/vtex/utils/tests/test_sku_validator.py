import uuid
from unittest.mock import Mock, patch

from django.test import TestCase
from django.core.cache import cache

from marketplace.wpp_products.models import Catalog
from marketplace.services.vtex.utils.sku_validator import SKUValidator


class MockVTEXService:
    """Mock service for VTEX operations"""

    def __init__(self):
        self.call_count = 0
        self.product_details_cache = {}

    def get_product_details(self, sku_id, domain):
        """Mock method that returns product details"""
        self.call_count += 1

        # Return predefined product details based on sku_id
        if sku_id in self.product_details_cache:
            return self.product_details_cache[sku_id]

        # Default product details
        return {
            "ProductName": f"Product {sku_id}",
            "ProductDescription": f"Description for product {sku_id}",
            "IsActive": True,
        }

    def set_product_details(self, sku_id, details):
        """Helper method to set product details for testing"""
        self.product_details_cache[sku_id] = details


class MockZeroShotClient:
    """Mock client for AI validation"""

    def __init__(self):
        self.call_count = 0
        self.validation_responses = {}

    def validate_product_policy(self, product_description):
        """Mock method for AI validation"""
        self.call_count += 1

        # Return predefined response based on description
        if product_description in self.validation_responses:
            return self.validation_responses[product_description]

        # Default valid response
        return {"output": {"classification": "Valid Product", "other": True}}

    def set_validation_response(self, description, classification, is_valid):
        """Helper method to set validation responses for testing"""
        self.validation_responses[description] = {
            "output": {"classification": classification, "other": is_valid}
        }


class TestSKUValidator(TestCase):
    """Test cases for SKUValidator class"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()

        # Create mock catalog instead of real Django object
        self.catalog = Mock(spec=Catalog)
        self.catalog.uuid = str(uuid.uuid4())
        self.catalog.name = "Test Catalog"

        # Create mock services
        self.mock_service = MockVTEXService()
        self.mock_zeroshot_client = MockZeroShotClient()

        # Create SKUValidator instance
        self.validator = SKUValidator(
            service=self.mock_service,
            domain="test-domain.com",
            zeroshot_client=self.mock_zeroshot_client,
        )

        # Clear cache before each test
        cache.clear()

        # Mock ProductValidation.objects to avoid database operations
        self.product_validation_patcher = patch(
            "marketplace.services.vtex.utils.sku_validator.ProductValidation"
        )
        self.mock_product_validation = self.product_validation_patcher.start()
        self.addCleanup(self.product_validation_patcher.stop)

    def test_init(self):
        """Test SKUValidator initialization"""
        self.assertEqual(self.validator.service, self.mock_service)
        self.assertEqual(self.validator.domain, "test-domain.com")
        self.assertEqual(self.validator.zeroshot_client, self.mock_zeroshot_client)
        self.assertEqual(self.validator.cache_prefix, "sku_validator")

    def test_get_cache_key(self):
        """Test cache key generation"""
        sku_id = "TEST-SKU-123"
        expected_key = f"sku_validator:{self.catalog.uuid}:{sku_id}"

        cache_key = self.validator._get_cache_key(self.catalog, sku_id)
        self.assertEqual(cache_key, expected_key)

    def test_get_cached_validation_with_cache_hit(self):
        """Test getting cached validation with cache hit"""
        cache_key = "test_cache_key"
        cached_data = (True, "Valid from cache")

        # Set cache
        cache.set(cache_key, cached_data, timeout=300)

        # Get cached validation
        result = self.validator._get_cached_validation(cache_key)

        self.assertEqual(result, cached_data)
        # Verify cache was renewed
        self.assertIsNotNone(cache.get(cache_key))

    def test_get_cached_validation_with_cache_miss(self):
        """Test getting cached validation with cache miss"""
        cache_key = "non_existent_key"

        result = self.validator._get_cached_validation(cache_key)

        self.assertIsNone(result)

    def test_validate_product_details_invalid_sku_id_none(self):
        """Test validation with None sku_id"""
        result = self.validator.validate_product_details(None, self.catalog)

        self.assertIsNone(result)

    def test_validate_product_details_invalid_sku_id_empty_string(self):
        """Test validation with empty string sku_id"""
        result = self.validator.validate_product_details("", self.catalog)

        self.assertIsNone(result)

    def test_validate_product_details_invalid_sku_id_non_string(self):
        """Test validation with non-string sku_id"""
        result = self.validator.validate_product_details(123, self.catalog)

        self.assertIsNone(result)

    def test_validate_product_details_cached_invalid(self):
        """Test validation with cached invalid result"""
        sku_id = "INVALID-SKU"
        cache_key = self.validator._get_cache_key(self.catalog, sku_id)

        # Set invalid cache
        cache.set(cache_key, (False, "Invalid from cache"), timeout=300)

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 0)

    def test_validate_product_details_cached_valid(self):
        """Test validation with cached valid result"""
        sku_id = "VALID-SKU"
        cache_key = self.validator._get_cache_key(self.catalog, sku_id)

        # Set valid cache
        cache.set(cache_key, (True, "Valid from cache"), timeout=300)

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNotNone(result)
        self.assertEqual(self.mock_service.call_count, 1)

    def test_validate_product_details_database_invalid(self):
        """Test validation with invalid database record"""
        sku_id = "DB-INVALID-SKU"

        # Mock database query to return invalid record
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = False
        self.mock_product_validation.objects.filter.return_value = mock_query

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 0)

        # Verify cache was set
        cache_key = self.validator._get_cache_key(self.catalog, sku_id)
        cached_result = cache.get(cache_key)
        self.assertEqual(cached_result, (False, "Invalid from database"))

    def test_validate_product_details_database_valid(self):
        """Test validation with valid database record"""
        sku_id = "DB-VALID-SKU"

        # Mock database query to return valid record
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = True
        self.mock_product_validation.objects.filter.return_value = mock_query

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNotNone(result)
        self.assertEqual(self.mock_service.call_count, 1)

        # Verify cache was set
        cache_key = self.validator._get_cache_key(self.catalog, sku_id)
        cached_result = cache.get(cache_key)
        self.assertEqual(cached_result, (True, "Valid from database"))

    def test_validate_product_details_no_product_details(self):
        """Test validation when service returns no product details"""
        sku_id = "NO-DETAILS-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock service to return None
        self.mock_service.set_product_details(sku_id, None)

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 1)

    def test_validate_product_details_inactive_product(self):
        """Test validation with inactive product"""
        sku_id = "INACTIVE-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock service to return inactive product
        self.mock_service.set_product_details(
            sku_id,
            {
                "ProductName": "Inactive Product",
                "ProductDescription": "This product is inactive",
                "IsActive": False,
            },
        )

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNotNone(result)
        self.assertEqual(result["IsActive"], False)
        self.assertEqual(self.mock_service.call_count, 1)

    def test_validate_product_details_ai_validation_invalid(self):
        """Test validation with AI validation returning invalid"""
        sku_id = "AI-INVALID-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock AI client to return invalid for the actual product description that will be generated
        self.mock_zeroshot_client.set_validation_response(
            "Product AI-INVALID-SKU. Description for product AI-INVALID-SKU",
            "Invalid Category",
            False,
        )

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 1)
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

        # Verify database record was created
        self.mock_product_validation.objects.create.assert_called_once()

    def test_validate_product_details_ai_validation_valid(self):
        """Test validation with AI validation returning valid"""
        sku_id = "AI-VALID-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNotNone(result)
        self.assertEqual(self.mock_service.call_count, 1)
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

        # Verify cache was set
        cache_key = self.validator._get_cache_key(self.catalog, sku_id)
        cached_result = cache.get(cache_key)
        self.assertIsNotNone(cached_result)
        self.assertTrue(cached_result[0])  # is_valid should be True

    def test_validate_product_details_long_description_truncation(self):
        """Test validation with long product description"""
        sku_id = "LONG-DESC-SKU"
        long_description = "A" * 10000  # 10k characters

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock service to return product with long description
        self.mock_service.set_product_details(
            sku_id,
            {
                "ProductName": "Product with Long Description",
                "ProductDescription": long_description,
                "IsActive": True,
            },
        )

        # Mock AI client to return invalid for the truncated description
        # The actual description will be "Product with Long Description. " + truncated description
        expected_description = "Product with Long Description. " + "A" * (
            9999 - len("Product with Long Description. ")
        )
        self.mock_zeroshot_client.set_validation_response(
            expected_description, "Invalid Category", False
        )

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 1)
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

        # Verify description was truncated to 9999 characters
        self.mock_product_validation.objects.create.assert_called_once()
        call_args = self.mock_product_validation.objects.create.call_args[1]
        self.assertEqual(len(call_args["description"]), 9999)

    def test_validate_with_ai_success(self):
        """Test AI validation with successful response"""
        product_description = "Valid product description"

        is_valid, classification = self.validator.validate_with_ai(product_description)

        self.assertTrue(is_valid)
        self.assertEqual(classification, "Valid Product")
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

    def test_validate_with_ai_exception(self):
        """Test AI validation with exception"""
        product_description = "Product that causes exception"

        # Mock zeroshot client to raise exception
        original_method = self.mock_zeroshot_client.validate_product_policy
        self.mock_zeroshot_client.validate_product_policy = Mock(
            side_effect=Exception("API Error")
        )

        is_valid, classification = self.validator.validate_with_ai(product_description)

        self.assertTrue(is_valid)
        self.assertEqual(classification, "Valid because exception")

        # Restore original method
        self.mock_zeroshot_client.validate_product_policy = original_method

    def test_validate_with_ai_invalid_classification(self):
        """Test AI validation with invalid classification"""
        product_description = "Invalid product description"

        # Mock AI client to return invalid
        self.mock_zeroshot_client.set_validation_response(
            product_description, "Invalid Category", False
        )

        is_valid, classification = self.validator.validate_with_ai(product_description)

        self.assertFalse(is_valid)
        self.assertEqual(classification, "Invalid Category")
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

    def test_validate_product_details_without_description(self):
        """Test validation with product without description"""
        sku_id = "NO-DESC-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock service to return product without description
        self.mock_service.set_product_details(
            sku_id,
            {
                "ProductName": "Product without description",
                "ProductDescription": None,
                "IsActive": True,
            },
        )

        # Mock AI client to return invalid for the product without description
        self.mock_zeroshot_client.set_validation_response(
            "Product without description", "Invalid Category", False
        )

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 1)
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

        # Verify only name was used for validation
        self.mock_product_validation.objects.create.assert_called_once()
        call_args = self.mock_product_validation.objects.create.call_args[1]
        self.assertEqual(call_args["description"], "Product without description")

    def test_validate_product_details_empty_description(self):
        """Test validation with product with empty description"""
        sku_id = "EMPTY-DESC-SKU"

        # Mock database query to return None (no record found)
        mock_query = Mock()
        mock_query.values_list.return_value.first.return_value = None
        self.mock_product_validation.objects.filter.return_value = mock_query

        # Mock service to return product with empty description
        self.mock_service.set_product_details(
            sku_id,
            {
                "ProductName": "Product with empty description",
                "ProductDescription": "",
                "IsActive": True,
            },
        )

        # Mock AI client to return invalid for the product with empty description
        self.mock_zeroshot_client.set_validation_response(
            "Product with empty description", "Invalid Category", False
        )

        result = self.validator.validate_product_details(sku_id, self.catalog)

        self.assertIsNone(result)
        self.assertEqual(self.mock_service.call_count, 1)
        self.assertEqual(self.mock_zeroshot_client.call_count, 1)

        # Verify only name was used for validation
        self.mock_product_validation.objects.create.assert_called_once()
        call_args = self.mock_product_validation.objects.create.call_args[1]
        self.assertEqual(call_args["description"], "Product with empty description")
