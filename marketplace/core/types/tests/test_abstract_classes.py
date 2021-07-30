import uuid

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.core.types.base import AppType
from marketplace.applications.models import AppTypeAsset, App
from marketplace.interactions.models import Rating, Comment


User = get_user_model()


class AppTypeTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_superuser(email="admin@marketplace.ai", password="fake@pass#$")

        class FakeType(AppType):
            code = "ftp"
            name = "Fake Type"
            description = "Type to test only"
            summary = "Type to test only"
            category = AppType.CATEGORY_CHANNEL
            developer = "Weni"
            bg_color = "#123A23"

        self.FakeType = FakeType

    def create_app_type_asset(self, fake_type_instance: AppType, user: User) -> AppTypeAsset:
        return AppTypeAsset.objects.create(
            app_code=fake_type_instance.code,
            asset_type=AppTypeAsset.ASSET_TYPE_ICON,
            attachment="../../tests/file_to_upload.txt",
            description="Test app type asset",
            created_by=user,
        )

    def test_list_assets_from_app_type(self):
        fake_type_instance = self.FakeType()

        self.assertFalse(fake_type_instance.assets.exists())

        self.create_app_type_asset(fake_type_instance, self.user)

        self.assertTrue(fake_type_instance.assets.exists())

    def test_list_apps_from_app_type(self):
        fake_type_instance = self.FakeType()

        self.assertFalse(fake_type_instance.apps.exists())

        App.objects.create(
            app_code=fake_type_instance.code,
            config={"test": "test"},
            org_uuid=uuid.uuid4(),
            platform=App.PLATFORM_WENI_FLOWS,
            created_by=self.user,
        )

        self.assertTrue(fake_type_instance.apps.exists())

    def test_list_ratings_from_app_type(self):
        fake_type_instance = self.FakeType()
        self.assertFalse(fake_type_instance.ratings.exists())

        rating = Rating.objects.create(
            app_code=fake_type_instance.code,
            created_by=self.user,
            rate=4,
        )

        self.assertTrue(fake_type_instance.ratings.exists())
        self.assertTrue(fake_type_instance.ratings.count() == 1)
        self.assertEqual(rating, fake_type_instance.ratings.first())

    def test_list_comments_from_app_type(self):
        fake_type_instance = self.FakeType()
        self.assertFalse(fake_type_instance.comments.exists())

        comment = Comment.objects.create(
            app_code=fake_type_instance.code,
            created_by=self.user,
            content="Fake comment to test the AppType",
        )

        self.assertTrue(fake_type_instance.comments.exists())
        self.assertTrue(fake_type_instance.comments.count() == 1)
        self.assertEqual(comment, fake_type_instance.comments.first())

    def test_get_icon_from_app_type_without_asset(self):
        fake_type_instance = self.FakeType()
        message = f"{self.FakeType.__name__} doesn't have an icon"

        with self.assertRaisesMessage(AppTypeAsset.DoesNotExist, message):
            fake_type_instance.get_icon_asset()

    def test_get_icon_from_app_type(self):
        fake_type_instance = self.FakeType()
        icon = self.create_app_type_asset(fake_type_instance, self.user)

        self.assertEqual(fake_type_instance.get_icon_asset(), icon)

    def test_get_icon_url_from_app_type(self):
        fake_type_instance = self.FakeType()
        icon = self.create_app_type_asset(fake_type_instance, self.user)

        self.assertEqual(fake_type_instance.get_icon_url(), icon.attachment.url)

    def test_get_category_display_from_app_type(self):
        fake_type_instance = self.FakeType()
        categories = dict(self.FakeType.CATEGORY_CHOICES)

        self.assertEqual(fake_type_instance.get_category_display(), categories[fake_type_instance.category])

    def test_get_ratings_average_from_app_type(self):
        fake_type_instance = self.FakeType()
        self.assertIsNone(fake_type_instance.get_ratings_average())

        Rating.objects.create(
            app_code=fake_type_instance.code,
            created_by=self.user,
            rate=4,
        )

        self.assertEqual(fake_type_instance.get_ratings_average(), 4.0)

        Rating.objects.create(
            app_code=fake_type_instance.code,
            created_by=User.objects.create_superuser(email="user@marketplace.ai", password="fake@pass#$"),
            rate=1,
        )

        self.assertEqual(fake_type_instance.get_ratings_average(), 2.5)
