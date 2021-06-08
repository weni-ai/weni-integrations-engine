from django.test import TestCase

from marketplace.accounts.models import User


class TestUserCreate(TestCase):
    def setUp(self):
        self.user_info = dict(email="fake@email.com", password="fake123pass")

    def test_create_user(self):
        user = User.objects.create_user(**self.user_info)

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_superuser)
        self.assertEqual(self.user_info["email"], user.email)

    def test_create_super_user(self):
        user = User.objects.create_superuser(**self.user_info)

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertEqual(self.user_info["email"], user.email)

    def test_empty_email(self):
        user_info = self.user_info
        user_info.update(email="")

        with self.assertRaises(ValueError):
            User.objects.create_superuser(**self.user_info)
