from unittest.mock import Mock, patch
from datetime import datetime
from django.test import TestCase

from marketplace.core.types.channels.whatsapp_base.requests.facebook import (
    FacebookConversationAPI,
    Conversations,
    PricingAnalytics,
    ConversationDataAdapter,
)


class FacebookConversationAPITestCase(TestCase):
    """Test cases for FacebookConversationAPI with dual API support"""

    def setUp(self):
        self.api = FacebookConversationAPI()
        self.waba_id = "test_waba_id"
        self.access_token = "test_access_token"

    def test_should_use_pricing_analytics_before_july_2025(self):
        """Test that legacy API is used for dates before July 2025"""
        # Convert date to timestamp for testing
        start_datetime = datetime(2025, 6, 1)
        start_timestamp = str(int(start_datetime.timestamp()))

        # Mock the conversations method to avoid real API calls
        with patch.object(
            self.api, "_get_conversations_from_legacy_api"
        ) as mock_legacy:
            mock_legacy.return_value = Mock()
            self.api.conversations(
                self.waba_id, self.access_token, start_timestamp, "1753891200"
            )

            # Should call legacy API
            mock_legacy.assert_called_once()

    def test_should_use_pricing_analytics_after_july_2025(self):
        """Test that pricing analytics API is used for dates after July 2025"""
        # Convert date to timestamp for testing
        start_datetime = datetime(2025, 7, 1)
        start_timestamp = str(int(start_datetime.timestamp()))

        # Mock the conversations method to avoid real API calls
        with patch.object(
            self.api, "_get_conversations_from_pricing_analytics"
        ) as mock_pricing:
            mock_pricing.return_value = Mock()
            self.api.conversations(
                self.waba_id, self.access_token, start_timestamp, "1753891200"
            )

            # Should call pricing analytics API
            mock_pricing.assert_called_once()

    def test_should_use_pricing_analytics_on_july_2025(self):
        """Test that pricing analytics API is used for July 1, 2025"""
        # Convert date to timestamp for testing
        start_datetime = datetime(2025, 7, 1)
        start_timestamp = str(int(start_datetime.timestamp()))

        # Mock the conversations method to avoid real API calls
        with patch.object(
            self.api, "_get_conversations_from_pricing_analytics"
        ) as mock_pricing:
            mock_pricing.return_value = Mock()
            self.api.conversations(
                self.waba_id, self.access_token, start_timestamp, "1753891200"
            )

            # Should call pricing analytics API
            mock_pricing.assert_called_once()

    def test_date_parsing(self):
        """Test that date parsing works correctly"""
        # Test parsing of July 1, 2025
        start_date = "7-1-2025"
        parsed_date = self.api._parse_date_string(start_date)
        self.assertEqual(parsed_date.year, 2025)
        self.assertEqual(parsed_date.month, 7)
        self.assertEqual(parsed_date.day, 1)

        # Test parsing of July 30, 2025
        end_date = "7-30-2025"
        parsed_end_date = self.api._parse_date_string(end_date)
        self.assertEqual(parsed_end_date.year, 2025)
        self.assertEqual(parsed_end_date.month, 7)
        self.assertEqual(parsed_end_date.day, 30)

    @patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.requests.get"
    )
    def test_conversations_legacy_api_mocked(self, mock_get):
        """Test conversations method with legacy API using mocks"""
        # Mock the response
        mock_response = Mock()
        mock_response.json.return_value = {
            "conversation_analytics": {
                "data": [
                    {
                        "data_points": [
                            {
                                "conversation_direction": "BUSINESS_INITIATED",
                                "conversation_category": "SERVICE",
                                "conversation": 10,
                            }
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Test with date before July 2025
        start_datetime = datetime(2025, 6, 1)
        start_timestamp = str(int(start_datetime.timestamp()))
        end_datetime = datetime(2025, 6, 30)
        end_timestamp = str(int(end_datetime.timestamp()))

        result = self.api.conversations(
            self.waba_id, self.access_token, start_timestamp, end_timestamp
        )

        self.assertIsInstance(result, Conversations)
        mock_get.assert_called_once()

    @patch(
        "marketplace.core.types.channels.whatsapp_base.requests.facebook.requests.get"
    )
    def test_conversations_pricing_api_mocked(self, mock_get):
        """Test conversations method with pricing analytics API using mocks"""
        # Mock the response
        mock_response = Mock()
        mock_response.json.return_value = {
            "pricing_analytics": {
                "data": [
                    {
                        "data_points": [
                            {"pricing_category": "SERVICE", "volume": 10, "cost": 0.0}
                        ]
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        # Test with date after July 2025
        start_datetime = datetime(2025, 7, 1)
        start_timestamp = str(int(start_datetime.timestamp()))
        end_datetime = datetime(2025, 7, 30)
        end_timestamp = str(int(end_datetime.timestamp()))

        result = self.api.conversations(
            self.waba_id, self.access_token, start_timestamp, end_timestamp
        )

        self.assertIsInstance(result, Conversations)
        mock_get.assert_called_once()


class PricingAnalyticsTestCase(TestCase):
    """Test cases for PricingAnalytics class"""

    def test_pricing_analytics_initialization(self):
        """Test PricingAnalytics initialization with valid data"""
        data = {
            "data": [
                {
                    "data_points": [
                        {"pricing_category": "SERVICE", "volume": 10, "cost": 0.0},
                        {"pricing_category": "UTILITY", "volume": 5, "cost": 0.04},
                    ]
                }
            ]
        }

        analytics = PricingAnalytics(data)

        self.assertEqual(analytics.total_volume, 15)
        self.assertEqual(analytics.breakdown_by_category["SERVICE"]["volume"], 10)
        self.assertEqual(analytics.breakdown_by_category["UTILITY"]["volume"], 5)

    def test_pricing_analytics_empty_data(self):
        """Test PricingAnalytics initialization with empty data"""
        analytics = PricingAnalytics(None)

        self.assertEqual(analytics.total_volume, 0)
        self.assertEqual(analytics.breakdown_by_category, {})


class ConversationDataAdapterTestCase(TestCase):
    """Test cases for ConversationDataAdapter class"""

    def test_adapter_converts_pricing_to_conversations_format(self):
        """Test that adapter correctly converts pricing analytics to conversations format"""
        # Create mock pricing analytics
        pricing_data = {
            "data": [
                {
                    "data_points": [
                        {"pricing_category": "SERVICE", "volume": 10, "cost": 0.0},
                        {"pricing_category": "UTILITY", "volume": 5, "cost": 0.04},
                    ]
                }
            ]
        }

        pricing_analytics = PricingAnalytics(pricing_data)
        adapter = ConversationDataAdapter(pricing_analytics)

        result = adapter.to_conversations_format()

        self.assertIsInstance(result, Conversations)
        # Should sum all volumes as business initiated
        self.assertEqual(result._business_initiated, 15)
        self.assertEqual(result._user_initiated, 0)


# Test individual components in isolation
class PricingAnalyticsIsolatedTestCase(TestCase):
    """Isolated test cases for PricingAnalytics to avoid data accumulation"""

    def test_pricing_analytics_initialization_isolated(self):
        """Test PricingAnalytics initialization with valid data in isolation"""
        data = {
            "data": [
                {
                    "data_points": [
                        {"pricing_category": "SERVICE", "volume": 10, "cost": 0.0},
                        {"pricing_category": "UTILITY", "volume": 5, "cost": 0.04},
                    ]
                }
            ]
        }

        analytics = PricingAnalytics(data)

        self.assertEqual(analytics.total_volume, 15)
        self.assertEqual(analytics.breakdown_by_category["SERVICE"]["volume"], 10)
        self.assertEqual(analytics.breakdown_by_category["UTILITY"]["volume"], 5)

    def test_pricing_analytics_empty_data_isolated(self):
        """Test PricingAnalytics initialization with empty data in isolation"""
        analytics = PricingAnalytics(None)

        self.assertEqual(analytics.total_volume, 0)
        self.assertEqual(analytics.breakdown_by_category, {})
