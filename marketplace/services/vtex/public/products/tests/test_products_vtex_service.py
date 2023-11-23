import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App
from marketplace.services.vtex.public.products.service import (
    PublicProductsService,
)


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
        response = self.service.is_domain_valid("valid.domain.com")
        self.assertTrue(response)

    def test_configure_valid(self):
        response = self.service.configure(self.app, "valid.domain.com")
        self.assertEqual(response.config, {"domain": "valid.domain.com"})

    def test_list_all_products(self):
        response = self.service.list_all_products("valid.domain.com")
        self.assertEqual(len(response), 1)

    # ================================
    # Invalid Domain
    # ================================

    def test_list_all_products_invalid_domain(self):
        with self.assertRaises(ValueError) as context:
            self.service.list_all_products("invalid.domain.com")
        self.assertTrue("The domain provided is invalid." in str(context.exception))

    def test_configure_invalid_domain(self):
        with self.assertRaises(ValueError) as context:
            self.service.configure(self.app, "invalid.domain.com")
        self.assertTrue("The domain provided is invalid." in str(context.exception))

    def test_is_domain_invalid_domain(self):
        response = self.service.is_domain_valid("invalid.domain.com")
        self.assertFalse(response)
