import uuid
import urllib
from typing import Tuple

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.conf import settings

from marketplace.applications.models import App, AppTypeAsset


User = get_user_model()


def create_app_type_asset(created_by: User) -> Tuple[dict, AppTypeAsset]:
    app_data = dict(
        app_slug="test_slug",
        asset_type=AppTypeAsset.ASSET_TYPE_ATTACHMENT,
        attachment="file_to_upload.txt",
        created_by=created_by,
    )

    return app_data, AppTypeAsset.objects.create(**app_data)


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


class TestModelAppTypeAsset(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.app_data, self.app_type_asset = create_app_type_asset(self.user)

    def test_created_app_type_asset_data(self):
        self.assertEqual(self.app_type_asset.app_slug, self.app_data["app_slug"])
        self.assertEqual(self.app_type_asset.asset_type, AppTypeAsset.ASSET_TYPE_ATTACHMENT)

    def test_url_from_attachment(self):
        expected_url = urllib.parse.urljoin(settings.MEDIA_URL, self.app_data["attachment"])
        self.assertEqual(expected_url, self.app_type_asset.attachment.url)


def TestModelAppTypeAssetMethods(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.app_data, self.app_type_asset = create_app_type_asset(self.user)

    def test_str_method(self):
        self.assertEqual(str(self.app_type_asset), self.app_data["app_slug"])
