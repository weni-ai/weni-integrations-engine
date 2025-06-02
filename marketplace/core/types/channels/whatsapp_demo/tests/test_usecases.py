from unittest.mock import MagicMock, patch

from django.test import TestCase

from marketplace.applications.models import App
from marketplace.core.types.channels.whatsapp_demo.usecases.whatsapp_demo_creation import (
    EnsureWhatsAppDemoAppUseCase,
)


class EnsureWhatsAppDemoAppUseCaseTest(TestCase):
    @patch(
        "marketplace.core.types.channels.whatsapp_demo.usecases.whatsapp_demo_creation.WPPRouterChannelClient"
    )
    @patch(
        "marketplace.core.types.channels.whatsapp_demo.type.WhatsAppDemoType"
    )
    def test_get_or_create_app_exists(
        self, mock_whatsapp_demo_type, mock_wpp_router_client
    ):
        project_uuid = "test_project_uuid"
        user = MagicMock()
        mock_app = MagicMock(spec=App)

        mock_whatsapp_demo_type.code = "wpp-demo"
        mock_filter = MagicMock()
        mock_filter.first.return_value = mock_app
        with patch.object(App.objects, "filter", return_value=mock_filter) as mock_app_filter:
            use_case = EnsureWhatsAppDemoAppUseCase(project_uuid, user)
            result = use_case.get_or_create()

        self.assertEqual(result, mock_app)
        mock_app_filter.assert_called_once_with(
            code="wpp-demo", project_uuid=project_uuid
        )
        mock_whatsapp_demo_type.assert_not_called()
        mock_wpp_router_client.assert_not_called()

    @patch(
        "marketplace.core.types.channels.whatsapp_demo.usecases.whatsapp_demo_creation.WPPRouterChannelClient"
    )
    @patch(
        "marketplace.core.types.channels.whatsapp_demo.type.WhatsAppDemoType"
    )
    def test_get_or_create_app_does_not_exist(
        self, mock_whatsapp_demo_type_class, mock_wpp_router_client_class
    ):
        project_uuid = "test_project_uuid"
        user = MagicMock()
        mock_created_app = MagicMock(spec=App)
        mock_configured_app = MagicMock(spec=App)

        # Mock the class instance and its methods
        mock_whatsapp_demo_type_instance = MagicMock()
        mock_whatsapp_demo_type_instance.create_app.return_value = mock_created_app
        mock_whatsapp_demo_type_class.return_value = mock_whatsapp_demo_type_instance
        mock_whatsapp_demo_type_class.code = "wpp-demo"  # Class attribute
        mock_whatsapp_demo_type_class.configure_app.return_value = mock_configured_app

        mock_filter = MagicMock()
        mock_filter.first.return_value = None  # App does not exist
        with patch.object(App.objects, "filter", return_value=mock_filter) as mock_app_filter:
            use_case = EnsureWhatsAppDemoAppUseCase(project_uuid, user)
            result = use_case.get_or_create()

        self.assertEqual(result, mock_configured_app)
        mock_app_filter.assert_called_once_with(
            code="wpp-demo", project_uuid=project_uuid
        )
        mock_whatsapp_demo_type_class.assert_called_once_with()
        mock_whatsapp_demo_type_instance.create_app.assert_called_once_with(
            project_uuid=project_uuid, created_by=user
        )
        mock_wpp_router_client_class.assert_called_once_with()
        mock_whatsapp_demo_type_class.configure_app.assert_called_once_with(
            mock_created_app, user, mock_wpp_router_client_class.return_value
        )
