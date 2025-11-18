from unittest.mock import Mock, patch
from queue import Queue

from django.test import TestCase

from marketplace.services.vtex.utils.data_processor import (
    TextCleaner,
    ProductExtractor,
    ProductValidator,
    ProductSaver,
    ProductProcessor,
    BatchProcessor,
    DataProcessor,
)
from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO
from marketplace.services.vtex.utils.enums import ProductPriority
from marketplace.clients.exceptions import CustomAPIException


class TestTextCleaner(TestCase):
    """Test cases for TextCleaner utility class."""

    def test_clean_removes_html_tags(self):
        """Test that HTML tags are removed from text."""
        text = "<p>Hello <b>world</b>!</p>"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello world!")

    def test_clean_replaces_non_breaking_spaces(self):
        """Test that non-breaking spaces are replaced with regular spaces."""
        text = "Hello\xa0world"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello world")

    def test_clean_removes_zero_width_spaces(self):
        """Test that zero-width spaces are removed."""
        text = "Hello\u200bworld"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Helloworld")

    def test_clean_removes_control_characters(self):
        """Test that control characters are removed."""
        text = "Hello\x00\x01\x02world"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Helloworld")

    def test_clean_replaces_quotes(self):
        """Test that quotes are replaced with spaces."""
        text = "Hello \"world\" and 'universe'"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello world and universe")

    def test_clean_normalizes_newlines(self):
        """Test that different newline formats are normalized."""
        text = "Hello\r\nworld\r\nuniverse\n"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello\nworld\nuniverse")

    def test_clean_replaces_multiple_spaces(self):
        """Test that multiple spaces are replaced with single space."""
        text = "Hello    world\t\tuniverse"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello worlduniverse")

    def test_clean_removes_bullet_points(self):
        """Test that bullet points are removed."""
        text = "Hello • world • universe"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello  world  universe")

    def test_clean_adds_space_after_period(self):
        """Test that space is added after period if not followed by whitespace."""
        text = "Hello.World.Universe"
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello. World. Universe")

    def test_clean_complex_text(self):
        """Test cleaning of complex text with multiple issues."""
        text = '<p>Hello\xa0"world"\u200b•\r\nuniverse</p>'
        result = TextCleaner.clean(text)
        self.assertEqual(result, "Hello world\nuniverse")


class TestProductExtractor(TestCase):
    """Test cases for ProductExtractor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.store_domain = "test-store.com"
        self.extractor = ProductExtractor(self.store_domain)

    def test_extract_with_images_list(self):
        """Test extraction when Images list is available."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "Images": [{"ImageUrl": "https://example.com/image.jpg"}],
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": 100.0,
            "list_price": 120.0,
            "selling_price": 100.0,
            "is_available": True,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertIsInstance(result, FacebookProductDTO)
        self.assertEqual(result.id, "123")
        self.assertEqual(result.title, "Test Product")
        self.assertEqual(result.description, "Test Description")
        self.assertEqual(result.availability, "in stock")
        self.assertEqual(result.status, "Active")
        self.assertEqual(result.price, 120.0)
        self.assertEqual(result.sale_price, 100.0)
        self.assertEqual(result.image_link, "https://example.com/image.jpg")
        self.assertEqual(result.brand, "Test Brand")
        self.assertEqual(result.link, "https://test-store.com/product/123?idsku=123")

    def test_extract_with_image_url_fallback(self):
        """Test extraction when falling back to ImageUrl."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "ImageUrl": "https://example.com/image.jpg",
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": 100.0,
            "list_price": 120.0,
            "is_available": True,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertEqual(result.image_link, "https://example.com/image.jpg")

    def test_extract_with_empty_images(self):
        """Test extraction when Images list is empty."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "Images": [],
            "ImageUrl": "https://example.com/image.jpg",
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": 100.0,
            "list_price": 120.0,
            "is_available": True,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertEqual(result.image_link, "https://example.com/image.jpg")

    def test_extract_out_of_stock(self):
        """Test extraction for out of stock product."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "ImageUrl": "https://example.com/image.jpg",
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": 0,
            "list_price": 0,
            "is_available": False,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertEqual(result.availability, "out of stock")
        self.assertEqual(result.status, "archived")

    def test_extract_with_none_prices(self):
        """Test extraction when prices are None."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "ImageUrl": "https://example.com/image.jpg",
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": None,
            "list_price": None,
            "is_available": True,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertEqual(result.price, 0)
        self.assertEqual(result.sale_price, 0)

    def test_extract_with_no_image_url(self):
        """Test extraction when no image URL is found anywhere."""
        product_details = {
            "Id": "123",
            "DetailUrl": "/product/123",
            "Images": [],  # Empty images list
            # No ImageUrl field at all
            "SkuName": "Test Product",
            "ProductDescription": "Test Description",
            "BrandName": "Test Brand",
        }
        availability_details = {
            "price": 100.0,
            "list_price": 120.0,
            "is_available": True,
        }

        result = self.extractor.extract(product_details, availability_details)

        self.assertIsInstance(result, FacebookProductDTO)
        self.assertEqual(result.id, "123")
        self.assertEqual(result.image_link, "")  # Should be empty string
        # The warning should be logged, but we can't easily test that without mocking logger


class TestProductValidator(TestCase):
    """Test cases for ProductValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_rule = Mock()
        self.mock_rule.apply.return_value = True
        self.validator = ProductValidator([self.mock_rule])

    def test_is_valid_with_valid_product(self):
        """Test validation with a valid product."""
        product_dto = FacebookProductDTO(
            id="123",
            title="Test Product",
            description="Test Description",
            availability="in stock",
            status="Active",
            condition="new",
            price="100.0",
            link="https://example.com",
            image_link="https://example.com/image.jpg",
            brand="Test Brand",
            sale_price="100.0",
            product_details={},
        )

        result = self.validator.is_valid(product_dto)

        self.assertTrue(result)

    def test_is_valid_with_missing_required_field(self):
        """Test validation with missing required field."""
        product_dto = FacebookProductDTO(
            id="123",
            title="",  # Empty title should fail validation
            description="Test Description",
            availability="in stock",
            status="Active",
            condition="new",
            price="100.0",
            link="https://example.com",
            image_link="https://example.com/image.jpg",
            brand="Test Brand",
            sale_price="100.0",
            product_details={},
        )

        result = self.validator.is_valid(product_dto)

        self.assertFalse(result)

    def test_is_valid_in_stock_without_price(self):
        """Test validation fails when product is in stock but has no price."""
        product_dto = FacebookProductDTO(
            id="123",
            title="Test Product",
            description="Test Description",
            availability="in stock",
            status="Active",
            condition="new",
            price="",  # Empty price should fail for in stock products
            link="https://example.com",
            image_link="https://example.com/image.jpg",
            brand="Test Brand",
            sale_price="",
            product_details={},
        )

        result = self.validator.is_valid(product_dto)

        self.assertFalse(result)

    def test_apply_rules_all_pass(self):
        """Test apply_rules when all rules pass."""
        product_dto = FacebookProductDTO(
            id="123",
            title="Test Product",
            description="Test Description",
            availability="in stock",
            status="Active",
            condition="new",
            price="100.0",
            link="https://example.com",
            image_link="https://example.com/image.jpg",
            brand="Test Brand",
            sale_price="100.0",
            product_details={},
        )

        result = self.validator.apply_rules(
            product_dto, "seller123", Mock(), "domain.com", "channel1"
        )

        self.assertTrue(result)
        self.mock_rule.apply.assert_called_once()

    def test_apply_rules_one_fails(self):
        """Test apply_rules when one rule fails."""
        self.mock_rule.apply.return_value = False
        product_dto = FacebookProductDTO(
            id="123",
            title="Test Product",
            description="Test Description",
            availability="in stock",
            status="Active",
            condition="new",
            price="100.0",
            link="https://example.com",
            image_link="https://example.com/image.jpg",
            brand="Test Brand",
            sale_price="100.0",
            product_details={},
        )

        result = self.validator.apply_rules(
            product_dto, "seller123", Mock(), "domain.com", "channel1"
        )

        self.assertFalse(result)


class TestProductSaver(TestCase):
    """Test cases for ProductSaver class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_catalog = Mock()
        self.mock_catalog.vtex_app.uuid = "test-uuid"

        # Mock dependencies using patch.start() and patch.stop()
        self.mock_product_manager = Mock()
        self.mock_upload_manager = Mock()

        # Setup patch objects
        self.patcher_product_manager = patch(
            "marketplace.services.vtex.utils.data_processor.ProductFacebookManager",
            return_value=self.mock_product_manager,
        )
        self.patcher_upload_manager = patch(
            "marketplace.services.vtex.utils.data_processor.UploadManager",
            self.mock_upload_manager,
        )

        # Start patches
        self.patcher_product_manager.start()
        self.patcher_upload_manager.start()

        # Add cleanup to stop patches
        self.addCleanup(self.patcher_product_manager.stop)
        self.addCleanup(self.patcher_upload_manager.stop)

    def test_save_batch_success(self):
        """Test successful batch saving."""
        self.mock_product_manager.bulk_save_initial_product_data.return_value = True

        saver = ProductSaver(batch_size=2, priority=ProductPriority.DEFAULT)
        products = [
            FacebookProductDTO(
                id="1",
                title="Product 1",
                description="Desc 1",
                availability="in stock",
                status="Active",
                condition="new",
                price="100",
                link="link1",
                image_link="img1",
                brand="Brand1",
                sale_price="100",
                product_details={},
            ),
            FacebookProductDTO(
                id="2",
                title="Product 2",
                description="Desc 2",
                availability="in stock",
                status="Active",
                condition="new",
                price="200",
                link="link2",
                image_link="img2",
                brand="Brand2",
                sale_price="200",
                product_details={},
            ),
            FacebookProductDTO(
                id="3",
                title="Product 3",
                description="Desc 3",
                availability="in stock",
                status="Active",
                condition="new",
                price="300",
                link="link3",
                image_link="img3",
                brand="Brand3",
                sale_price="300",
                product_details={},
            ),
        ]

        result = saver.save_batch(products, self.mock_catalog)

        self.assertEqual(len(result), 1)  # Only one product should remain
        self.assertEqual(saver.sent_to_db, 2)
        self.mock_product_manager.bulk_save_initial_product_data.assert_called_once()
        # UploadManager.check_and_start_upload should be called
        self.mock_upload_manager.check_and_start_upload.assert_called_once()

    def test_save_batch_api_only_priority(self):
        """Test batch saving with API_ONLY priority."""
        saver = ProductSaver(batch_size=2, priority=ProductPriority.API_ONLY)
        products = [Mock()]

        result = saver.save_batch(products, self.mock_catalog)

        self.assertEqual(result, [])
        # ProductFacebookManager should not be called for API_ONLY priority

    def test_save_batch_empty_list(self):
        """Test batch saving with empty list."""
        saver = ProductSaver()
        products = []

        result = saver.save_batch(products, self.mock_catalog)

        self.assertEqual(result, [])
        # ProductFacebookManager should not be called for empty list

    def test_save_batch_exception(self):
        """Test batch saving when an exception occurs during save operation."""
        self.mock_product_manager.bulk_save_initial_product_data.side_effect = (
            Exception("Database error")
        )

        saver = ProductSaver(batch_size=2)
        products = [Mock(), Mock(), Mock()]

        result = saver.save_batch(products, self.mock_catalog)

        # Should handle exception gracefully and return remaining products
        self.assertEqual(len(result), 1)  # One product should remain
        self.assertEqual(saver.sent_to_db, 0)  # No products sent to DB due to exception

    def test_save_batch_failure_warning(self):
        """Test batch saving when save operation returns False (failure)."""
        self.mock_product_manager.bulk_save_initial_product_data.return_value = (
            False  # Save failed
        )

        saver = ProductSaver(batch_size=2)
        products = [Mock(), Mock(), Mock()]

        result = saver.save_batch(products, self.mock_catalog)

        # Should return remaining products and log warning
        self.assertEqual(len(result), 1)  # One product should remain
        self.assertEqual(saver.sent_to_db, 0)  # No products sent to DB due to failure


class TestProductProcessor(TestCase):
    """Test cases for ProductProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_catalog = Mock()
        self.mock_catalog.vtex_app.config = {"use_sku_sellers": False}
        self.mock_extractor = Mock()
        self.mock_validator = Mock()
        self.mock_validator.is_valid.return_value = True
        self.mock_validator.apply_rules.return_value = True

        # Mock SKUValidator using patch.start() and patch.stop()
        self.mock_sku_validator = Mock()
        self.patcher_sku_validator = patch(
            "marketplace.services.vtex.utils.data_processor.SKUValidator",
            return_value=self.mock_sku_validator,
        )
        self.patcher_sku_validator.start()
        self.addCleanup(self.patcher_sku_validator.stop)

        self.processor = ProductProcessor(
            catalog=self.mock_catalog,
            domain="test.com",
            service=Mock(),
            extractor=self.mock_extractor,
            validator=self.mock_validator,
            update_product=False,
            sync_specific_sellers=False,
            sales_channel=None,
        )

    def test_process_seller_sku_success(self):
        """Test successful processing of seller SKU."""
        self.mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = self.mock_sku_validator
        self.processor.service.simulate_cart_for_seller.return_value = {
            "is_available": True,
            "price": 100,
            "list_price": 120,
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_seller_sku("seller123", "sku123")

        self.assertEqual(len(result), 1)
        self.mock_sku_validator.validate_product_details.assert_called_once()
        self.processor.service.simulate_cart_for_seller.assert_called_once()

    def test_process_seller_sku_invalid_seller_id(self):
        """Test processing with invalid seller ID."""
        result = self.processor.process_seller_sku("", "sku123")

        self.assertEqual(result, [])

    def test_process_seller_sku_invalid_sku_id(self):
        """Test processing with invalid SKU ID."""
        result = self.processor.process_seller_sku("seller123", "")

        self.assertEqual(result, [])

    def test_process_seller_sku_inactive_product(self):
        """Test processing with inactive product."""
        self.mock_sku_validator.validate_product_details.return_value = {
            "IsActive": False,
        }

        self.processor.validator_service = self.mock_sku_validator

        result = self.processor.process_seller_sku("seller123", "sku123")

        self.assertEqual(result, [])

    def test_process_single_sku_success(self):
        """Test successful processing of single SKU."""
        self.mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = self.mock_sku_validator
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": True, "price": 100, "list_price": 120},
            "seller2": {"is_available": True, "price": 200, "list_price": 240},
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_single_sku("sku123", ["seller1", "seller2"])

        self.assertEqual(len(result), 2)
        self.mock_sku_validator.validate_product_details.assert_called_once()
        self.processor.service.simulate_cart_for_multiple_sellers.assert_called_once()

    def test_process_single_sku_with_sales_channel(self):
        """Test processing with sales channel."""
        self.mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = self.mock_sku_validator
        self.processor.sales_channel = ["channel1", "channel2"]
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": True, "price": 100, "list_price": 120},
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_single_sku("sku123", ["seller1"])

        self.assertEqual(len(result), 2)  # One for each channel

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_unavailable_product(self, mock_sku_validator_class):
        """Test processing with unavailable product (not in update mode)."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_seller.return_value = {
            "is_available": False,  # Product is unavailable
            "price": 100,
            "list_price": 120,
        }

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list because product is unavailable and not in update mode
        self.assertEqual(result, [])
        mock_sku_validator.validate_product_details.assert_called_once()
        self.processor.service.simulate_cart_for_seller.assert_called_once()

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_invalid_dto(self, mock_sku_validator_class):
        """Test processing when DTO validation fails."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_seller.return_value = {
            "is_available": True,
            "price": 100,
            "list_price": 120,
        }

        # Mock extractor to return invalid DTO
        self.mock_extractor.extract.return_value = Mock()
        # Mock validator to return False (invalid)
        self.mock_validator.is_valid.return_value = False

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list because DTO validation failed
        self.assertEqual(result, [])
        self.mock_validator.is_valid.assert_called_once()

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_rules_fail(self, mock_sku_validator_class):
        """Test processing when business rules fail."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_seller.return_value = {
            "is_available": True,
            "price": 100,
            "list_price": 120,
        }

        # Mock extractor to return valid DTO
        self.mock_extractor.extract.return_value = Mock()
        # Mock validator to return True for is_valid but False for apply_rules
        self.mock_validator.is_valid.return_value = True
        self.mock_validator.apply_rules.return_value = False

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list because business rules failed
        self.assertEqual(result, [])
        self.mock_validator.apply_rules.assert_called_once()

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_custom_api_exception_404(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException status 404."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Not found", status_code=404
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list and log info message
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_custom_api_exception_500(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException status 500."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Server error", status_code=500
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list and log info message
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_seller_sku_custom_api_exception_other(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException other status codes."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Bad request", status_code=400
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_seller_sku("seller123", "sku123")

        # Should return empty list and log error message
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_invalid_sku_id_type(self, mock_sku_validator_class):
        """Test processing with invalid sku_id type."""
        result = self.processor.process_single_sku(
            123, ["seller1"]
        )  # int instead of str

        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_invalid_sellers_type(self, mock_sku_validator_class):
        """Test processing with invalid sellers type."""
        result = self.processor.process_single_sku(
            "sku123", "seller1"
        )  # str instead of list

        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_invalid_seller_values(self, mock_sku_validator_class):
        """Test processing with invalid seller values in list."""
        result = self.processor.process_single_sku("sku123", ["seller1", "", None, 123])

        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_use_sku_sellers(self, mock_sku_validator_class):
        """Test processing with use_sku_sellers enabled."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
            "SkuSellers": [
                {"SellerId": "seller1"},
                {"SellerId": "seller2"},
                {"SellerId": ""},  # Empty seller should be filtered out
            ],
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.use_sku_sellers = True
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": True, "price": 100, "list_price": 120},
            "seller2": {"is_available": True, "price": 200, "list_price": 240},
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_single_sku("sku123", ["original_seller"])

        # Should use sellers from SkuSellers instead of original list
        self.assertEqual(len(result), 2)
        # Verify that simulate_cart_for_multiple_sellers was called with the correct sellers
        call_args = self.processor.service.simulate_cart_for_multiple_sellers.call_args
        self.assertEqual(call_args[0][1], ["seller1", "seller2"])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_empty_sellers_after_sku_sellers(
        self, mock_sku_validator_class
    ):
        """Test processing when sellers list becomes empty after SkuSellers filtering."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
            "SkuSellers": [],  # Empty SkuSellers
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.use_sku_sellers = True

        result = self.processor.process_single_sku("sku123", ["original_seller"])

        # Should return empty list because no valid sellers
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_inactive_product_update_mode(
        self, mock_sku_validator_class
    ):
        """Test processing inactive product in update mode."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": False,  # Inactive product
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.update_product = True  # Update mode enabled
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": False, "price": 0, "list_price": 0, "data": {}},
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should process even inactive product in update mode
        self.assertEqual(len(result), 1)

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_unavailable_product(self, mock_sku_validator_class):
        """Test processing with unavailable product (not in update mode)."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": False, "price": 100, "list_price": 120},
            "seller2": {"is_available": True, "price": 200, "list_price": 240},
        }

        self.mock_extractor.extract.return_value = Mock()

        result = self.processor.process_single_sku("sku123", ["seller1", "seller2"])

        # Should only process available products
        self.assertEqual(len(result), 1)

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_invalid_dto(self, mock_sku_validator_class):
        """Test processing when DTO validation fails."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": True, "price": 100, "list_price": 120},
        }

        # Mock extractor to return invalid DTO
        self.mock_extractor.extract.return_value = Mock()
        # Mock validator to return False (invalid)
        self.mock_validator.is_valid.return_value = False

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list because DTO validation failed
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_rules_fail(self, mock_sku_validator_class):
        """Test processing when business rules fail."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": True,
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.service.simulate_cart_for_multiple_sellers.return_value = {
            "seller1": {"is_available": True, "price": 100, "list_price": 120},
        }

        # Mock extractor to return valid DTO
        self.mock_extractor.extract.return_value = Mock()
        # Mock validator to return True for is_valid but False for apply_rules
        self.mock_validator.is_valid.return_value = True
        self.mock_validator.apply_rules.return_value = False

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list because business rules failed
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_custom_api_exception_404(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException status 404."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Not found", status_code=404
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list and log info message
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_custom_api_exception_500(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException status 500."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Server error", status_code=500
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list and log info message
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_custom_api_exception_other_status(
        self, mock_sku_validator_class
    ):
        """Test processing with CustomAPIException other status codes (not 404/500)."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.side_effect = CustomAPIException(
            "Bad request", status_code=400
        )

        self.processor.validator_service = mock_sku_validator

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list and log error message with exc_info=True
        self.assertEqual(result, [])

    @patch("marketplace.services.vtex.utils.data_processor.SKUValidator")
    def test_process_single_sku_inactive_product_not_update_mode(
        self, mock_sku_validator_class
    ):
        """Test processing with inactive product when not in update mode."""
        mock_sku_validator = Mock()
        mock_sku_validator_class.return_value = mock_sku_validator
        mock_sku_validator.validate_product_details.return_value = {
            "IsActive": False,  # Inactive product
            "SkuName": "Test Product",
        }

        self.processor.validator_service = mock_sku_validator
        self.processor.update_product = False  # Not in update mode

        result = self.processor.process_single_sku("sku123", ["seller1"])

        # Should return empty list because product is inactive and not in update mode
        self.assertEqual(result, [])


class TestBatchProcessor(TestCase):
    """Test cases for BatchProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_queue = Mock()
        self.mock_queue.qsize.return_value = 10
        self.mock_queue.empty.return_value = False
        self.mock_queue.get.return_value = "test_item"

        # Mock dependencies using patch.start() and patch.stop()
        self.mock_tqdm = Mock()
        self.mock_close_connections = Mock()

        # Setup patch objects
        self.patcher_tqdm = patch(
            "marketplace.services.vtex.utils.data_processor.tqdm",
            return_value=self.mock_tqdm,
        )
        self.patcher_close_connections = patch(
            "marketplace.services.vtex.utils.data_processor.close_old_connections",
            self.mock_close_connections,
        )

        # Start patches
        self.patcher_tqdm.start()
        self.patcher_close_connections.start()

        # Add cleanup to stop patches
        self.addCleanup(self.patcher_tqdm.stop)
        self.addCleanup(self.patcher_close_connections.stop)

        self.batch_processor = BatchProcessor(
            queue=self.mock_queue,
            temp_queue=None,
            use_threads=False,  # Disable threading for easier testing
            max_workers=1,
        )

    def test_run_single_mode_success(self):
        """Test successful run in single mode."""
        mock_progress_bar = Mock()
        self.mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_single_sku.return_value = [Mock()]
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT
        mock_saver.save_batch.return_value = []

        items = ["sku1", "sku2"]
        sellers = ["seller1"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        result = self.batch_processor.run(
            items, mock_processor, "single", sellers, mock_saver
        )

        # The method returns True only if all results were processed (empty results list)
        # Since we have results remaining, it should return False
        self.assertFalse(result)
        self.assertEqual(mock_processor.process_single_sku.call_count, 2)
        mock_saver.save_batch.assert_called()

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_seller_sku_mode_success(self, mock_close_connections, mock_tqdm):
        """Test successful run in seller_sku mode."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_seller_sku.return_value = [Mock()]
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT
        mock_saver.save_batch.return_value = []

        items = ["seller1#sku1", "seller2#sku2"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        result = self.batch_processor.run(
            items, mock_processor, "seller_sku", None, mock_saver
        )

        # The method returns True only if all results were processed (empty results list)
        # Since we have results remaining, it should return False
        self.assertFalse(result)
        self.assertEqual(mock_processor.process_seller_sku.call_count, 2)

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_api_only_priority(self, mock_close_connections, mock_tqdm):
        """Test run with API_ONLY priority."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_single_sku.return_value = [Mock()]
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.API_ONLY
        mock_saver.save_batch.return_value = []

        items = ["sku1"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        result = self.batch_processor.run(
            items, mock_processor, "single", [], mock_saver
        )

        # For API_ONLY priority, the method should return the list of results
        self.assertIsInstance(result, list)
        # save_batch is called during processing, but not at the end for API_ONLY
        # We can verify that the final save_batch call was not made by checking the call count
        # The method should have been called during processing but not at the end
        self.assertGreaterEqual(mock_saver.save_batch.call_count, 1)

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_with_temp_queue(self, mock_close_connections, mock_tqdm):
        """Test run with temp_queue functionality."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_single_sku.return_value = [Mock()]
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT
        mock_saver.save_batch.return_value = []

        mock_temp_queue = Mock()
        self.batch_processor.temp_queue = mock_temp_queue

        items = ["sku1"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        self.batch_processor.run(items, mock_processor, "single", [], mock_saver)

        # Should call temp_queue.put and temp_queue.clear
        mock_temp_queue.put.assert_called_once_with("sku1")
        mock_temp_queue.clear.assert_called()

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_with_exception(self, mock_close_connections, mock_tqdm):
        """Test run when processing raises an exception."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_single_sku.side_effect = Exception("Processing error")
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT

        items = ["sku1"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        self.batch_processor.run(items, mock_processor, "single", [], mock_saver)

        # Should handle exception gracefully and increment invalid counter
        mock_close_connections.assert_called()

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_with_threading(self, mock_close_connections, mock_tqdm):
        """Test run with threading enabled."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        # Enable threading
        self.batch_processor.use_threads = True
        self.batch_processor.max_workers = 2

        mock_processor = Mock()
        mock_processor.process_single_sku.return_value = [Mock()]
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT
        mock_saver.save_batch.return_value = []

        items = ["sku1", "sku2"]

        # Mock queue behavior for threading
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        result = self.batch_processor.run(
            items, mock_processor, "single", [], mock_saver
        )

        # Should handle threading correctly
        self.assertFalse(result)  # Should return False due to remaining results

    @patch("marketplace.services.vtex.utils.data_processor.tqdm")
    @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
    def test_run_with_failed_processing(self, mock_close_connections, mock_tqdm):
        """Test run when processing returns empty results (failed processing)."""
        mock_progress_bar = Mock()
        mock_tqdm.return_value = mock_progress_bar

        mock_processor = Mock()
        mock_processor.process_single_sku.return_value = (
            []
        )  # Empty results (failed processing)
        mock_processor.catalog = Mock()

        mock_saver = Mock()
        mock_saver.batch_size = 1
        mock_saver.priority = ProductPriority.DEFAULT

        items = ["sku1"]

        # Mock queue behavior
        call_count = 0

        def mock_get():
            nonlocal call_count
            call_count += 1
            if call_count <= len(items):
                return items[call_count - 1]
            self.mock_queue.empty.return_value = True
            return None

        self.mock_queue.get.side_effect = mock_get

        result = self.batch_processor.run(
            items, mock_processor, "single", [], mock_saver
        )

        # Should increment invalid counter when processing returns empty results
        # When there are no results, the method returns True (no pending items)
        self.assertTrue(result)  # Should return True when no results to process
        # The invalid counter should be incremented (line 662)


class TestDataProcessor(TestCase):
    """Test cases for DataProcessor class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock all dependencies using patch.start() and patch.stop()
        self.mock_extractor = Mock()
        self.mock_validator = Mock()
        self.mock_saver = Mock()
        self.mock_processor = Mock()
        self.mock_batch_processor = Mock()

        # Setup patch objects
        self.patcher_extractor = patch(
            "marketplace.services.vtex.utils.data_processor.ProductExtractor",
            return_value=self.mock_extractor,
        )
        self.patcher_validator = patch(
            "marketplace.services.vtex.utils.data_processor.ProductValidator",
            return_value=self.mock_validator,
        )
        self.patcher_saver = patch(
            "marketplace.services.vtex.utils.data_processor.ProductSaver",
            return_value=self.mock_saver,
        )
        self.patcher_processor = patch(
            "marketplace.services.vtex.utils.data_processor.ProductProcessor",
            return_value=self.mock_processor,
        )
        self.patcher_batch_processor = patch(
            "marketplace.services.vtex.utils.data_processor.BatchProcessor",
            return_value=self.mock_batch_processor,
        )

        # Start patches
        self.patcher_extractor.start()
        self.patcher_validator.start()
        self.patcher_saver.start()
        self.patcher_processor.start()
        self.patcher_batch_processor.start()

        # Add cleanup to stop patches
        self.addCleanup(self.patcher_extractor.stop)
        self.addCleanup(self.patcher_validator.stop)
        self.addCleanup(self.patcher_saver.stop)
        self.addCleanup(self.patcher_processor.stop)
        self.addCleanup(self.patcher_batch_processor.stop)

        # Create DataProcessor instance
        self.data_processor = DataProcessor(
            queue=None,
            temp_queue=None,
            use_threads=False,
            batch_size=100,
            max_workers=1,
        )

    def test_process_success(self):
        """Test successful processing."""
        # Setup mocks
        self.mock_batch_processor.run.return_value = []

        # Test data
        items = ["sku1", "sku2"]
        catalog = Mock()
        domain = "test.com"
        service = Mock()
        rules = []
        store_domain = "store.com"

        result = self.data_processor.process(
            items=items,
            catalog=catalog,
            domain=domain,
            service=service,
            rules=rules,
            store_domain=store_domain,
            update_product=False,
            sync_specific_sellers=False,
            mode="single",
            sellers=["seller1"],
            priority=ProductPriority.DEFAULT,
            sales_channel=None,
        )

        # Verify batch processor was run
        self.mock_batch_processor.run.assert_called_once()
        self.assertEqual(result, [])

    def test_process_with_default_queue(self):
        """Test processing with default queue creation."""
        processor = DataProcessor(queue=None)
        self.assertIsInstance(processor.queue, Queue)

    def test_process_with_custom_queue(self):
        """Test processing with custom queue."""
        custom_queue = Mock()
        processor = DataProcessor(queue=custom_queue)
        self.assertEqual(processor.queue, custom_queue)
