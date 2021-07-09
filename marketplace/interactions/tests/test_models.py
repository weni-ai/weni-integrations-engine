from typing import Tuple

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.interactions.models import Rating


User = get_user_model()


def create_rating(created_by: User) -> Tuple[User, dict, Rating]:

    data = dict(
        app_slug="test_slug",
        created_by=created_by,
        rate=5,
    )

    return created_by, data, Rating.objects.create(**data)


class TestModelRating(TestCase):
    def setUp(self):
        user = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")
        self.user, self.rating_data, self.rating = create_rating(user)

    def test_created_rating_data(self):
        self.assertEqual(self.rating.app_slug, self.rating_data["app_slug"])
        self.assertEqual(self.rating.rate, self.rating_data["rate"])


class TestModelRatingMethods(TestCase):
    def setUp(self):
        user = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")
        self.user, self.rating_data, self.rating = create_rating(user)

    def test_str_method(self):
        created_by = self.rating_data["created_by"]
        rate = self.rating_data["rate"]

        self.assertEquals(str(self.rating), f"{rate} - {created_by.email}")
