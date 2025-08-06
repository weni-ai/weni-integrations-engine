import requests
from datetime import datetime
from typing import Dict, List, Optional
from requests.models import Response

from ..exceptions import FacebookApiException

from django.conf import settings

WHATSAPP_VERSION = settings.WHATSAPP_VERSION

# Define the cutoff date for pricing analytics API (July 1, 2025)
PRICING_ANALYTICS_CUTOFF_DATE = datetime(2025, 7, 1)


class Conversations(object):
    """Legacy conversations data structure for backward compatibility"""

    _user_initiated = 0
    _business_initiated = 0
    _templates = {}

    def __init__(self, conversation_analytics: dict) -> None:
        if conversation_analytics is not None:
            data = conversation_analytics.get("data")
            data_points = self._get_data_points(data)

            self._calculate_conversation(data_points)

    @property
    def _total(self) -> int:
        return self._user_initiated + self._business_initiated

    def _calculate_conversation(self, data_points: list) -> None:
        self._templates = {}

        for data_point in data_points:
            conversation_direction = data_point.get("conversation_direction")
            conversation_category = data_point.get("conversation_category")
            conversation_count = data_point.get("conversation")

            if conversation_direction == "BUSINESS_INITIATED":
                self._business_initiated += conversation_count
            elif conversation_direction == "USER_INITIATED":
                self._user_initiated += conversation_count

            if conversation_category != "UNKNOWN":
                if conversation_category in self._templates:
                    self._templates[conversation_category] += conversation_count
                else:
                    self._templates[conversation_category] = conversation_count

    def _get_data_points(self, data: list):
        data_points_dict = next(
            filter(lambda data_content: "data_points" in data_content, data)
        )
        return data_points_dict.get("data_points")

    def __dict__(self) -> dict:
        templates_total = sum(self._templates.values())
        templates = {**self._templates, "total": templates_total}
        return dict(
            user_initiated=self._user_initiated,
            business_initiated=self._business_initiated,
            total=self._total,
            templates=templates,
            grand_total=self._total + templates_total,
        )


class PricingAnalytics(object):
    """New pricing analytics data structure for July 2025 onwards"""

    def __init__(self, pricing_analytics: dict) -> None:
        # Reset all data to avoid accumulation between instances
        self._data_points = []
        self._total_volume = 0
        self._breakdown_by_category = {}

        if pricing_analytics is not None:
            data = pricing_analytics.get("data")
            self._data_points = self._get_data_points(data)
            self._calculate_metrics()

    def _get_data_points(self, data: list):
        if not data:
            return []
        data_points_dict = next(
            filter(lambda data_content: "data_points" in data_content, data), {}
        )
        return data_points_dict.get("data_points", [])

    def _calculate_metrics(self) -> None:
        for data_point in self._data_points:
            volume = data_point.get("volume", 0)
            pricing_category = data_point.get("pricing_category")

            self._total_volume += int(volume) if volume else 0

            if pricing_category:
                if pricing_category not in self._breakdown_by_category:
                    self._breakdown_by_category[pricing_category] = {"volume": 0}
                self._breakdown_by_category[pricing_category]["volume"] += (
                    int(volume) if volume else 0
                )

    def __dict__(self) -> dict:
        return {
            "total_volume": self._total_volume,
            "breakdown_by_category": self._breakdown_by_category,
        }

    @property
    def total_volume(self) -> int:
        return self._total_volume

    @property
    def breakdown_by_category(self) -> dict:
        return self._breakdown_by_category


class ConversationDataAdapter:
    """Adapter to convert pricing analytics data to conversation format for backward compatibility"""

    def __init__(self, pricing_analytics: PricingAnalytics):
        self.pricing_analytics = pricing_analytics

    def to_conversations_format(self) -> Conversations:
        """Convert pricing analytics data to legacy conversations format"""
        # Create a mock conversation analytics structure
        mock_conversation_analytics = {
            "data": [{"data_points": self._convert_to_conversation_data_points()}]
        }
        return Conversations(mock_conversation_analytics)

    def _convert_to_conversation_data_points(self) -> List[Dict]:
        """Convert pricing analytics data points to conversation format"""
        data_points = []
        breakdown = self.pricing_analytics.breakdown_by_category

        # Map pricing categories to conversation categories
        category_mapping = {
            "SERVICE": "SERVICE",
            "UTILITY": "UTILITY",
            "MARKETING": "MARKETING",
            "MARKETING_LITE": "MARKETING_LITE",
            "AUTHENTICATION": "AUTHENTICATION",
        }

        for pricing_category, data in breakdown.items():
            volume = data.get("volume", 0)

            # Create data point in conversation format
            data_point = {
                "conversation_direction": "BUSINESS_INITIATED",  # Default for pricing analytics
                "conversation_category": category_mapping.get(
                    pricing_category, "UNKNOWN"
                ),
                "conversation": volume,
            }
            data_points.append(data_point)

        return data_points


class FacebookConversationAPI(object):
    """Facebook API client for conversations and pricing analytics"""

    def __init__(self):
        # Use the global cutoff date constant
        self._cutoff_date = PRICING_ANALYTICS_CUTOFF_DATE

    def _validate_response(self, response: Response):
        """Validate API response and raise exception if error"""
        error = response.json().get("error", None)
        if error is not None:
            raise FacebookApiException(error.get("message"))

    def _request(self, *args, **kwargs) -> Response:
        """Make HTTP request to Facebook API"""
        response = requests.get(*args, **kwargs)
        self._validate_response(response)
        return response

    def _parse_date_string(self, date_str: str) -> datetime:
        """
        Parse date string in format M-D-YYYY to datetime.

        Args:
            date_str: Date string in M-D-YYYY format (e.g., "7-1-2025")

        Returns:
            datetime object
        """
        return datetime.strptime(date_str, "%m-%d-%Y")

    def _should_use_pricing_analytics(self, start_date: str) -> bool:
        """
        Determine if we should use pricing analytics API based on billing period.

        Args:
            start_date: Start date in M-D-YYYY format (e.g., "7-1-2025")

        Returns:
            True if pricing analytics API should be used (July 1, 2025 onwards)
            False if legacy conversations API should be used (before July 1, 2025)
        """
        start_datetime = self._parse_date_string(start_date)
        return start_datetime >= self._cutoff_date

    def _get_conversation_fields(self, start: str, end: str) -> str:
        """Generate fields parameter for legacy conversations API"""
        fields = "conversation_analytics"
        fields += f".start({start})"
        fields += f".end({end})"
        fields += ".granularity(DAILY)"
        fields += ".phone_numbers([])"
        fields += ".conversation_types([])"
        fields += '.dimensions(["conversation_type", "conversation_direction", "conversation_category"])'
        return fields

    def _get_pricing_fields(
        self,
        start: str,
        end: str,
        dimensions: Optional[List[str]] = None,
    ) -> str:
        """Generate fields parameter for pricing analytics API"""
        if dimensions is None:
            dimensions = ["PRICING_CATEGORY"]

        fields = "pricing_analytics"
        fields += f".start({start})"
        fields += f".end({end})"
        fields += ".granularity(DAILY)"
        fields += ".phone_numbers([])"
        fields += ".country_codes([])"
        fields += ".metric_types([])"
        fields += ".pricing_types([])"
        fields += ".pricing_categories([])"

        dimensions_str = '","'.join(dimensions)
        fields += f'.dimensions(["{dimensions_str}"])'

        return fields

    def _parse_to_unix(self, time: datetime) -> str:
        utc_time = time.replace(tzinfo=None)
        return str(int(utc_time.timestamp()))

    def conversations(
        self, waba_id: str, access_token: str, start: str, end: str
    ) -> Conversations:
        """
        Get conversation data using appropriate API based on date range.

        Args:
            waba_id: WhatsApp Business Account ID
            access_token: Facebook access token
            start: Start timestamp (Unix timestamp as string)
            end: End timestamp (Unix timestamp as string)

        Returns:
            Conversations object with conversation data
        """
        # Convert timestamp to datetime for date comparison
        start_datetime = datetime.fromtimestamp(int(start))

        if start_datetime >= self._cutoff_date:
            return self._get_conversations_from_pricing_analytics(
                waba_id, access_token, start, end
            )
        else:
            return self._get_conversations_from_legacy_api(
                waba_id, access_token, start, end
            )

    def _get_conversations_from_legacy_api(
        self, waba_id: str, access_token: str, start: str, end: str
    ) -> Conversations:
        """Get conversation data using legacy conversations API"""
        # start and end are already Unix timestamps
        fields = self._get_conversation_fields(start, end)
        params = dict(fields=fields, access_token=access_token)

        response = self._request(
            f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}", params=params
        )
        conversation_analytics = response.json().get("conversation_analytics")

        return Conversations(conversation_analytics)

    def _get_conversations_from_pricing_analytics(
        self, waba_id: str, access_token: str, start: str, end: str
    ) -> Conversations:
        """Get conversation data using new pricing analytics API"""
        # start and end are already Unix timestamps
        fields = self._get_pricing_fields(start, end)
        params = dict(fields=fields, access_token=access_token)

        response = self._request(
            f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}", params=params
        )
        pricing_analytics_data = response.json().get("pricing_analytics")

        pricing_analytics = PricingAnalytics(pricing_analytics_data)
        adapter = ConversationDataAdapter(pricing_analytics)

        return adapter.to_conversations_format()

    def pricing_analytics(
        self,
        waba_id: str,
        access_token: str,
        start: str,
        end: str,
        dimensions: Optional[List[str]] = None,
    ) -> PricingAnalytics:
        """
        Get pricing analytics data directly.

        Args:
            waba_id: WhatsApp Business Account ID
            access_token: Facebook access token
            start: Start date in M-D-YYYY format
            end: End date in M-D-YYYY format
            dimensions: List of dimensions to include in response

        Returns:
            PricingAnalytics object with pricing data
        """
        start_timestamp = self._parse_to_unixtime(start)
        end_timestamp = self._parse_to_unixtime(end)

        fields = self._get_pricing_fields(start_timestamp, end_timestamp, dimensions)
        params = dict(fields=fields, access_token=access_token)

        response = self._request(
            f"https://graph.facebook.com/{WHATSAPP_VERSION}/{waba_id}", params=params
        )
        pricing_analytics_data = response.json().get("pricing_analytics")

        return PricingAnalytics(pricing_analytics_data)
