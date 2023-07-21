from django.test import TestCase, RequestFactory
from django.contrib import admin as django_admin

from marketplace.accounts.backends import User
from marketplace.applications.admin import AppTypeAssetAdmin, AppTypeFeaturedAdmin
from marketplace.applications.models import AppTypeAsset, AppTypeFeatured


class AppTypeFeaturedAdminTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@weni.ai", first_name="User", last_name="Test"
        )

        self.app_type_featured = AppTypeFeatured.objects.create(
            code="test-code", created_by=self.user, modified_by=self.user
        )

        self.factory = RequestFactory()

    def test_save_model_new_object(self):
        request = self.factory.post(
            "/",
            data={
                "code": "test-code",
                "created_by": self.user,
                "modified_by": self.user,
            },
        )

        request.user = self.user

        app_type_featured_admin = AppTypeFeaturedAdmin(
            AppTypeFeatured, django_admin.site
        )

        app_type_featured_admin.save_model(request, self.app_type_featured, None, False)

        self.assertEqual(self.app_type_featured.created_by, self.user)
        self.assertEqual(self.app_type_featured.modified_by, self.user)

        self.assertEqual(self.app_type_featured.priority, 1)

    def test_save_model_existing_object(self):
        request = self.factory.post("/", data={"code": "test-code"})

        request.user = self.user

        admin = AppTypeFeaturedAdmin(AppTypeFeatured, django_admin.site)
        admin.save_model(request, self.app_type_featured, None, True)

        self.assertEqual(self.app_type_featured.modified_by, self.user)

        self.assertEqual(self.app_type_featured.priority, 1)


class AppTypeAssetAdminTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@weni.ai", first_name="User", last_name="Test"
        )

        self.app_type_asset = AppTypeAsset.objects.create(
            code="test-code", created_by=self.user, modified_by=self.user
        )

        self.factory = RequestFactory()

    def test_save_model_new_object(self):
        request = self.factory.post("/", data={"name": "Test Asset", "type": "image"})

        request.user = self.user

        app_type_asset_admin = AppTypeAssetAdmin(AppTypeAsset, django_admin.site)

        app_type_asset_admin.save_model(request, self.app_type_asset, None, False)

        self.assertEqual(self.app_type_asset.created_by, self.user)
        self.assertEqual(self.app_type_asset.modified_by, self.user)

    def test_save_model_existing_object(self):
        request = self.factory.post("/", data={"name": "Test Asset", "type": "image"})

        request.user = self.user

        app_type_asset_admin = AppTypeAssetAdmin(AppTypeAsset, django_admin.site)

        app_type_asset_admin.save_model(request, self.app_type_asset, None, True)

        self.assertEqual(self.app_type_asset.modified_by, self.user)
