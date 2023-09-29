import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from marketplace.applications.models import App
from marketplace.wpp_products.models import Catalog


User = get_user_model()


class CreateCatalogErrorTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

    def test_create_catalog_with_error(self):
        app = App.objects.create(
            code="wpp",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )
        with self.assertRaises(ValidationError) as context:
            Catalog.objects.create(
                app=app,
                facebook_catalog_id="0123456789",
                name="catalog test error",
                category="commerce",
            )

        expected_error_message = "The App must be a 'WhatsApp Cloud' AppType."
        self.assertIn(expected_error_message, str(context.exception))


class CreateCatalogSuccessTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(email="user@marketplace.ai")

    def test_create_catalog_success(self):
        app = App.objects.create(
            code="wpp-cloud",
            created_by=self.user,
            project_uuid=str(uuid.uuid4()),
            platform=App.PLATFORM_WENI_FLOWS,
        )

        catalog = Catalog.objects.create(
            app=app,
            facebook_catalog_id="0123456789",
            name="catalog test success",
            category="commerce",
        )
        self.assertEqual(app.uuid, catalog.app.uuid)
