from unittest import TestCase
from unittest.mock import Mock
from uuid import UUID

from marketplace.core.types.channels.whatsapp_cloud.usecases.whatsapp_insights_sync import (
    WhatsAppInsightsSyncUseCase,
)
from marketplace.applications.models import App
from marketplace.services.insights.service import InsightsService


class TestWhatsAppInsightsSyncUseCase(TestCase):
    """Test case for WhatsAppInsightsSyncUseCase to verify proper integration with Insights service."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app_uuid = UUID("12345678-1234-5678-1234-567812345678")
        self.project_uuid = UUID("98765432-9876-5432-9876-987654321098")

        # Mock App with complete configuration
        self.app = Mock(spec=App)
        self.app.uuid = self.app_uuid
        self.app.project_uuid = self.project_uuid
        self.app.config = {
            "wa_waba_id": "123456789",
            "wa_phone_number_id": "987654321",
            "wa_number": "+5511999999999",
        }

        self.insights_service = Mock(spec=InsightsService)
        self.use_case = WhatsAppInsightsSyncUseCase(
            app=self.app, insights_service=self.insights_service
        )

    def test_prepare_whatsapp_data_with_complete_data(self):
        """Test that WhatsApp data is correctly prepared when all required fields are present."""
        expected_data = {
            "app_uuid": str(self.app_uuid),
            "project_uuid": str(self.project_uuid),
            "waba_id": "123456789",
            "phone_number": {
                "id": "987654321",
                "display_phone_number": "+5511999999999",
            },
        }

        result = self.use_case._prepare_whatsapp_data()
        self.assertEqual(result, expected_data)

    def test_prepare_whatsapp_data_with_missing_waba_id(self):
        """Test that preparation returns None when WABA ID is missing."""
        self.app.config = {
            "wa_phone_number_id": "987654321",
            "wa_number": "+5511999999999",
        }

        result = self.use_case._prepare_whatsapp_data()
        self.assertIsNone(result)

    def test_prepare_whatsapp_data_with_missing_phone_number_id(self):
        """Test that preparation returns None when phone number ID is missing."""
        self.app.config = {
            "wa_waba_id": "123456789",
            "wa_number": "+5511999999999",
        }

        result = self.use_case._prepare_whatsapp_data()
        self.assertIsNone(result)

    def test_prepare_whatsapp_data_with_missing_display_number(self):
        """Test that preparation returns None when display phone number is missing."""
        self.app.config = {
            "wa_waba_id": "123456789",
            "wa_phone_number_id": "987654321",
        }

        result = self.use_case._prepare_whatsapp_data()
        self.assertIsNone(result)

    def test_prepare_whatsapp_data_with_missing_app_uuid(self):
        """Test that preparation returns None when app UUID is missing."""
        self.app.uuid = None
        result = self.use_case._prepare_whatsapp_data()
        self.assertIsNone(result)

    def test_prepare_whatsapp_data_with_missing_project_uuid(self):
        """Test that preparation returns None when project UUID is missing."""
        self.app.project_uuid = None
        result = self.use_case._prepare_whatsapp_data()
        self.assertIsNone(result)

    def test_sync_with_complete_data(self):
        """Test that sync correctly calls insights service when all data is present."""
        expected_data = {
            "app_uuid": str(self.app_uuid),
            "project_uuid": str(self.project_uuid),
            "waba_id": "123456789",
            "phone_number": {
                "id": "987654321",
                "display_phone_number": "+5511999999999",
            },
        }

        self.use_case.sync()
        self.insights_service.create_whatsapp_integration.assert_called_once_with(
            expected_data
        )

    def test_sync_with_missing_data(self):
        """Test that sync doesn't call insights service when required data is missing."""
        self.app.config = {}  # Simulate missing data
        self.use_case.sync()
        self.insights_service.create_whatsapp_integration.assert_not_called()

    def test_insights_service_initialization_when_none_is_provided(self):
        """Test that insights service is automatically created when not provided."""
        use_case = WhatsAppInsightsSyncUseCase(app=self.app)
        self.assertIsInstance(use_case._insights_service, InsightsService)
