import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.services.vtex.public.products.service import (
    PublicProductsService,
)
from marketplace.services.vtex.exceptions import CredentialsValidationError

User = get_user_model()


class MockClient:
    def list_products(self, domain):
        return [
            {
                "productId": "6494",
                "productName": "Limão Taiti",
                "brand": "Sem Marca",
                "other_fields": "...",
            }
        ]

    def check_domain(self, domain):
        return domain == "valid.domain.com"


class TestVtexPublicProducts(TestCase):
    def setUp(self):
        user, _bool = User.objects.get_or_create(email="user-fbaservice@marketplace.ai")
        self.service = PublicProductsService(client=MockClient())
        self.app = App.objects.create(
            code="vtex",
            config={},
            created_by=user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

    # ================================
    # Valid Domain
    # ================================

    def test_is_domain_valid(self):
        response = self.service.check_is_valid_domain("valid.domain.com")
        self.assertTrue(response)

    def test_list_all_products(self):
        response = self.service.list_all_products("valid.domain.com")
        self.assertEqual(len(response), 1)

    # ================================
    # Invalid Domain
    # ================================

    def test_list_all_products_invalid_domain(self):
        with self.assertRaises(CredentialsValidationError) as context:
            self.service.list_all_products("invalid.domain.com")
        self.assertTrue(
            "The credentials provided are invalid." in str(context.exception)
        )

    def test_is_domain_invalid_domain(self):
        with self.assertRaises(CredentialsValidationError) as context:
            self.service.check_is_valid_domain("invalid.domain.com")
        self.assertTrue(
            "The credentials provided are invalid." in str(context.exception)
        )
