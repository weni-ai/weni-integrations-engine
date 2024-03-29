from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from marketplace.interactions.models import Rating, Comment


User = get_user_model()


class TestModelRatingMixin:
    def setUp(self):
        super().setUp()

        self.user = User.objects.create(
            email="admin@marketplace.ai", password="fake@pass#$"
        )

        self.rating_data = dict(
            code="wwc",
            created_by=self.user,
            rate=5,
        )

        self.rating = Rating.objects.create(**self.rating_data)


class TestModelRating(TestModelRatingMixin, TestCase):
    def test_created_rating_data(self):
        self.assertEqual(self.rating.code, self.rating_data["code"])
        self.assertEqual(self.rating.rate, self.rating_data["rate"])

    def test_unique_constraint_between_created_by_and_code(self):
        with self.assertRaises(IntegrityError):
            Rating.objects.create(**self.rating_data)


class TestModelRatingMethods(TestModelRatingMixin, TestCase):
    """
    Test all methods from model Rating
    """

    def test_str_method(self):
        created_by = self.rating_data["created_by"]
        rate = self.rating_data["rate"]

        self.assertEquals(str(self.rating), f"{rate} - {created_by.email}")

    def test_get_apptype_average_method(self):
        self.assertEqual(Rating.get_apptype_average("wwc"), 5.0)

        self.rating_data["rate"] = 2
        self.rating_data["created_by"] = User.objects.create_superuser(
            email="user@marketplace.ai",
            password="fake@pass#$",
        )
        Rating.objects.create(**self.rating_data)

        self.assertEqual(Rating.get_apptype_average("wwc"), 3.5)


class TestModelCommentMixin:
    def setUp(self):
        super().setUp()

        self.user = User.objects.create(
            email="admin@marketplace.ai", password="fake@pass#$"
        )

        self.comment_data = dict(
            code="wwc",
            created_by=self.user,
            content="This is a test comment",
        )

        self.comment = Comment.objects.create(**self.comment_data)


class TestModelComment(TestModelCommentMixin, TestCase):
    def test_created_comment_data(self):
        self.assertEqual(self.comment.code, self.comment_data["code"])
        self.assertEqual(self.comment.content, self.comment_data["content"])


class TestModelCommentMethods(TestModelCommentMixin, TestCase):
    """
    Test all methods from model Comment
    """

    def test_str_method(self):
        self.assertEqual(self.comment.content, str(self.comment))
