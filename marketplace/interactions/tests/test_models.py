from typing import Tuple

from django.test import TestCase
from django.contrib.auth import get_user_model

from marketplace.interactions.models import Rating, Comment


User = get_user_model()


def create_rating() -> Tuple[User, dict, Rating]:
    created_by = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")

    data = dict(
        app_slug="test_slug",
        created_by=created_by,
        rate=5,
    )

    return created_by, data, Rating.objects.create(**data)


class TestModelRating(TestCase):
    def setUp(self):
        self.user, self.rating_data, self.rating = create_rating()

    def test_created_rating_data(self):
        self.assertEqual(self.rating.app_slug, self.rating_data["app_slug"])
        self.assertEqual(self.rating.rate, self.rating_data["rate"])


class TestModelRatingMethods(TestCase):
    """
    Test all methods from model Rating
    """
    def setUp(self):
        self.user, self.rating_data, self.rating = create_rating()

    def test_str_method(self):
        created_by = self.rating_data["created_by"]
        rate = self.rating_data["rate"]

        self.assertEquals(str(self.rating), f"{rate} - {created_by.email}")


class TestModelCommentMixin:

    def setUp(self):
        super().setUp()

        self.user = User.objects.create(email="admin@marketplace.ai", password="fake@pass#$")

        self.comment_data = dict(
            app_slug="test_slug",
            created_by=self.user,
            content="This is a test comment",
        )

        self.comment = Comment.objects.create(**self.comment_data)


class TestModelComment(TestModelCommentMixin, TestCase):
    def test_created_comment_data(self):
        self.assertEqual(self.comment.app_slug, self.comment_data["app_slug"])
        self.assertEqual(self.comment.content, self.comment_data["content"])


class TestModelCommentMethods(TestModelCommentMixin, TestCase):
    """
    Test all methods from model Comment
    """
    def test_str_method(self):
        self.assertEqual(self.comment.content, str(self.comment))