from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.interactions.views import CommentViewSet
from marketplace.interactions.models import Comment


class CreateCommentViewTestCase(APIBaseTestCase):
    url = reverse("apptype-comment-list", kwargs={"apptype_pk": "wwc"})
    view_class = CommentViewSet

    def setUp(self):
        super().setUp()
        self.body = {"content": "This is only a test content"}

    @property
    def view(self):
        return self.view_class.as_view(self.ACTION_CREATE)

    def test_request_status_ok(self):
        response = self.request.post(self.url, self.body, apptype_pk="wwc")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_comment_without_content(self):
        response = self.request.post(self.url, {}, apptype_pk="wwc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.json)

    def test_create_comment_data(self):
        response = self.request.post(self.url, self.body, apptype_pk="wwc")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json["content"], self.body["content"])
        self.assertIn("app_code", response.json)
        self.assertIn("uuid", response.json)
        self.assertIn("created_on", response.json)
        self.assertFalse(response.json["edited"])
        self.assertTrue(response.json["owned"])


class RetrieveCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet

    def setUp(self):
        super().setUp()

        self.comment = Comment.objects.create(
            app_code="wwc",
            created_by=self.user,
            content="This is only a test content",
        )

        self.url = reverse("apptype-comment-detail", kwargs={"apptype_pk": "wwc", "pk": self.comment.pk})

    @property
    def view(self):
        return self.view_class.as_view(self.ACTION_RETRIEVE)

    def test_request_status_ok(self):
        response = self.request.get(self.url, apptype_pk="wwc", pk=self.comment.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_comment_data(self):
        response = self.request.get(self.url, apptype_pk="wwc", pk=self.comment.pk)
        self.assertEqual(response.json["content"], self.comment.content)
        self.assertIn("app_code", response.json)
        self.assertIn("uuid", response.json)
        self.assertIn("created_on", response.json)
        self.assertFalse(response.json["edited"])
        self.assertTrue(response.json["owned"])


class UpdateCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet

    def setUp(self):
        super().setUp()

        self.body = {"content": "This is the comment test modified"}

        self.comment = Comment.objects.create(
            app_code="wwc",
            created_by=self.user,
            content="This is only a test content",
        )

        self.url = reverse("apptype-comment-detail", kwargs={"apptype_pk": "wwc", "pk": self.comment.pk})

    @property
    def view(self):
        return self.view_class.as_view(self.ACTION_UPDATE)

    def get_updated_comment(self) -> Comment:
        return Comment.objects.get(pk=self.comment.pk)

    def test_request_status_ok(self):
        response = self.request.put(self.url, self.body, apptype_pk="wwc", pk=self.comment.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_modified_by_with_other_user_on_update(self):
        created_by = self.comment.created_by

        self.request.set_user(self.super_user)
        response = self.request.put(self.url, self.body, apptype_pk="wwc", pk=self.comment.pk)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json["owned"])
        self.assertNotEqual(self.comment.modified_by, created_by)
        self.assertEqual(self.comment.created_by, created_by)

    def test_comment_edited_after_update(self):
        self.assertFalse(self.comment.edited)

        response = self.request.put(self.url, self.body, apptype_pk="wwc", pk=self.comment.pk)
        updated_comment = self.get_updated_comment()

        self.assertTrue(updated_comment.edited)
        self.assertTrue(response.json["edited"])

    def test_update_comment_data(self):
        response = self.request.put(self.url, self.body, apptype_pk="wwc", pk=self.comment.pk)
        updated_comment = self.get_updated_comment()

        self.assertEqual(self.body["content"], updated_comment.content)
        self.assertIn("app_code", response.json)
        self.assertIn("uuid", response.json)
        self.assertIn("created_on", response.json)
        self.assertTrue(response.json["owned"])


class DestroyCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet

    def setUp(self):
        super().setUp()

        self.comment = Comment.objects.create(
            app_code="wwc",
            created_by=self.user,
            content="This is only a test content",
        )

        self.url = reverse("apptype-comment-detail", kwargs={"apptype_pk": "wwc", "pk": self.comment.pk})

    @property
    def view(self):
        return self.view_class.as_view(self.ACTION_DESTROY)

    def test_request_status_ok(self):
        response = self.request.delete(self.url, apptype_pk="wwc", pk=self.comment.pk)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(response.json)

    def test_comment_right_deleted(self):
        self.request.delete(self.url, apptype_pk="wwc", pk=self.comment.pk)
        self.assertFalse(Comment.objects.filter(pk=self.comment.pk).exists())


class ListCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet
    url = reverse("apptype-comment-list", kwargs={"apptype_pk": "wwc"})

    def setUp(self):
        super().setUp()
        self.comments_count = 10

        for comment in range(self.comments_count):
            Comment.objects.create(
                app_code="wwc",
                created_by=self.user,
                content=f"This is only a test content ({comment})",
            )

    @property
    def view(self):
        return self.view_class.as_view(self.ACTION_LIST)

    def test_request_status_ok(self):
        response = self.request.get(self.url, apptype_pk="wwc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_comments_count(self):
        response = self.request.get(self.url, apptype_pk="wwc")
        self.assertEqual(len(response.json), self.comments_count)
