import uuid
import urllib
from typing import Tuple

from django.test import TestCase, override_settings
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from marketplace.applications.models import App, AppTypeAsset, AppTypeFeatured
from marketplace.core import types


User = get_user_model()


def create_apptype_asset(created_by: User) -> Tuple[dict, AppTypeAsset]:
    app_data = dict(
        code="wwc",
        asset_type=AppTypeAsset.ASSET_TYPE_ICON,
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
            project_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            code="wwc",
            created_by=self.user,
        )

        self.app = App.objects.create(**self.app_data)

    def test_created_app_data(self):
        self.assertEqual(self.app.config, self.config)
        self.assertEqual(self.app.project_uuid, self.app_data["project_uuid"])
        self.assertEqual(self.app.platform, App.PLATFORM_WENI_FLOWS)
        self.assertEqual(self.app.code, self.app_data["code"])

    def test_str_method(self):
        self.assertEqual(str(self.app), self.app_data["code"])


@override_settings(USE_S3=False)
class TestModelAppTypeAsset(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.app_data, self.apptype_asset = create_apptype_asset(self.user)

    def test_created_apptype_asset_data(self):
        self.assertEqual(self.apptype_asset.code, self.app_data["code"])
        self.assertEqual(self.apptype_asset.asset_type, AppTypeAsset.ASSET_TYPE_ICON)

    def test_url_from_attachment(self):
        expected_url = urllib.parse.urljoin(settings.MEDIA_URL, self.app_data["attachment"])
        self.assertEqual(expected_url, self.apptype_asset.attachment.url)

    def test_unique_constraint_between_asset_type_and_code(self):
        with self.assertRaises(IntegrityError):
            create_apptype_asset(self.user)


class TestModelAppTypeAssetMethods(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.app_data, self.apptype_asset = create_apptype_asset(self.user)

    def test_str_method(self):
        self.assertEqual(str(self.apptype_asset), f"{self.apptype_asset.apptype.name} - Icon")


class TestModelAppTypeFeatured(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.apptype_featured = AppTypeFeatured.objects.create(code="wwc", created_by=self.user)

    def test_created_apptype_featured_data(self):
        self.assertEqual(self.apptype_featured.code, "wwc")
        self.assertEqual(self.apptype_featured.created_by, self.user)

    def test_unique_code_constraint(self):
        with self.assertRaises(IntegrityError):
            AppTypeFeatured.objects.create(code="wwc", created_by=self.user)


class TestModelAppTypeFeaturedMethods(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")
        self.apptype_featured = AppTypeFeatured.objects.create(code="wwc", created_by=self.user)

    def test_str_method(self):
        self.assertEqual(str(self.apptype_featured), self.apptype_featured.apptype.name)

    def test_apptype_method(self):
        self.assertEqual(self.apptype_featured.apptype, types.get_type("wwc"))

    def test_get_apptype_featureds(self):
        apptype = next(self.apptype_featured.get_apptype_featureds())
        self.assertEqual(apptype, types.get_type("wwc"))
