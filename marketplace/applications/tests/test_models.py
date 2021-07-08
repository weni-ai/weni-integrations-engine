import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.applications.models import App


User = get_user_model()


class TestModelApp(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.config = dict(fakekey="fakevalue")

        self.app_data = dict(
            config=self.config,
            org_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            app_slug="test_slug",
            created_by=self.user,
        )

        self.app = App.objects.create(**self.app_data)

    def test_created_app_data(self):
        self.assertEqual(self.app.config, self.config)
        self.assertEqual(self.app.org_uuid, self.app_data["org_uuid"])
        self.assertEqual(self.app.platform, App.PLATFORM_WENI_FLOWS)
        self.assertEqual(self.app.app_slug, self.app_data["app_slug"])

    def test_str_method(self):
        self.assertEqual(str(self.app), self.app_data["app_slug"])
