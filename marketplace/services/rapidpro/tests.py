from unittest import TestCase
from unittest.mock import Mock

from marketplace.services.rapidpro.service import RapidproService
from marketplace.interfaces.rapidpro.protocol import RapidproClientProtocol


class RapidproServiceTestCase(TestCase):
    def setUp(self):
        self.mock_client = Mock(spec=RapidproClientProtocol)
        self.service = RapidproService(client=self.mock_client)

        self.catalog = Mock()
        self.catalog.name = "Test Catalog"
        self.catalog.facebook_catalog_id = "12345"
        self.catalog.vtex_app.uuid = "uuid-1234"

        self.incident_name = "Test Incident"
        self.exception = Exception("Test Exception")

    def test_create_notification(self):
        self.service.create_notification(
            self.catalog, self.incident_name, self.exception
        )

        self.mock_client.send_alert.assert_called_once_with(
            self.incident_name,
            "integrations",
            {
                "catalog_name": self.catalog.name,
                "catalog_id": self.catalog.facebook_catalog_id,
                "app_vtex_uuid": str(self.catalog.vtex_app.uuid),
                "error": str(self.exception),
            },
        )
