from django.test import TestCase

from unittest.mock import Mock

from marketplace.services.vtex.exceptions import CredentialsValidationError
from marketplace.services.vtex.private.products.service import PrivateProductsService


class MockClient:
    def is_valid_credentials(self, domain):
        return domain == "valid.domain.com"

    def check_domain(self, domain):
        return domain in ["valid.domain.com", "another.valid.com"]


class PrivateProductsServiceTestCase(TestCase):
    def setUp(self):
        self.mock_client = MockClient()
        self.service = PrivateProductsService(self.mock_client)

    def test_check_is_valid_domain_valid(self):
        self.assertTrue(self.service.check_is_valid_domain("valid.domain.com"))

    def test_check_is_valid_domain_invalid(self):
        with self.assertRaises(CredentialsValidationError):
            self.service.check_is_valid_domain("invalid.domain.com")

    def test_validate_private_credentials_valid(self):
        self.assertTrue(self.service.validate_private_credentials("valid.domain.com"))

    def test_validate_private_credentials_invalid_domain(self):
        with self.assertRaises(CredentialsValidationError):
            self.service.validate_private_credentials("invalid.domain.com")

    def test_validate_private_credentials_invalid_credentials(self):
        self.mock_client.is_valid_credentials = Mock(return_value=False)
        result = self.service.validate_private_credentials("valid.domain.com")
        self.assertFalse(result)
