import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from rest_framework.exceptions import NotFound

from marketplace.applications.models import App
from marketplace.core.types.ecommerce.vtex.usecases.vtex_integration import (
    VtexIntegration,
)


User = get_user_model()


class VtexIntegrationTest(TestCase):
    def setUp(self):
        self.project_uuid = uuid.uuid4()

        self.user = User.objects.create_superuser(
            email="admin@marketplace.ai", password="fake@pass#$"
        )

        self.vtex_app = App.objects.create(
            code="vtex",
            project_uuid=self.project_uuid,
            created_by=self.user,
            config={
                "operator_token": {
                    "app_key": "key123",
                    "app_token": "token123",
                    "domain": "vtex.com",
                }
            },
        )

    def test_get_integration_details_success(self):
        # Test if VTEX integration credentials are returned correctly
        result = VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(result["app_key"], "key123")
        self.assertEqual(result["app_token"], "token123")
        self.assertEqual(result["domain"], "https://vtex.com")

    def test_get_integration_details_not_found(self):
        # Test if the NotFound exception is raised when the App is not found
        invalid_uuid = uuid.uuid4()
        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(invalid_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "A vtex-app integration was not found for the provided project UUID.",
        )

    def test_ensure_https_with_http(self):
        # Test if ensure_https method correctly adds 'https://' to the domain
        domain = "vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, "https://vtex.com")

    def test_ensure_https_already_secure(self):
        # Test if ensure_https method does not modify domains that already start with 'https://'
        domain = "https://vtex.com"
        result = VtexIntegration.ensure_https(domain)
        self.assertEqual(result, domain)

    def test_ensure_https_empty(self):
        # Test if ensure_https method handles None and empty strings correctly
        result = VtexIntegration.ensure_https(None)
        self.assertIsNone(result)

        result = VtexIntegration.ensure_https("")
        self.assertEqual(result, "")

    def test_get_integration_details_operator_token_not_found(self):
        # Test whether the NotFound exception is raised when the operator_token is not found
        # Remove operator_token from App configuration
        self.vtex_app.config.pop("operator_token")
        self.vtex_app.save()

        with self.assertRaises(NotFound) as context:
            VtexIntegration.vtex_integration_detail(self.project_uuid)

        self.assertEqual(
            str(context.exception.detail),
            "The operator_token was not found for the provided project UUID.",
        )
