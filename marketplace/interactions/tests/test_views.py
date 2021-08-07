from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status

from marketplace.core.tests.base import APIBaseTestCase
from marketplace.interactions.views import CommentViewSet
from marketplace.interactions.models import Comment


class CreateCommentViewTestCase(APIBaseTestCase):
    url = reverse("comments-list", kwargs={"app_code": "wwc"})
    view_class = CommentViewSet

    def setUp(self):
        super().setUp()
        self.body = {"content": "This is only a test content"}

    @property
    def view(self):
        return self.view_class.as_view({"post": "create"})

    def test_request_status_ok(self):
        response = self.request.post(self.url, self.body, app_code="wwc")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_comment_without_content(self):
        response = self.request.post(self.url, app_code="wwc")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.json)

    def test_create_comment_with_valid_body(self):
        response = self.request.post(self.url, self.body, app_code="wwc")
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

        self.url = reverse("comments-detail", kwargs={"app_code": "wwc", "pk": self.comment.pk})

    @property
    def view(self):
        return self.view_class.as_view({"get": "retrieve"})

    def test_request_status_ok(self):
        response = self.request.get(self.url, app_code="wwc", pk=self.comment.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_comment_data(self):
        response = self.request.get(self.url, app_code="wwc", pk=self.comment.pk)
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

        self.url = reverse("comments-detail", kwargs={"app_code": "wwc", "pk": self.comment.pk})

    @property
    def view(self):
        return self.view_class.as_view({"put": "update"})

    def test_request_status_ok(self):
        # print(self.url)
        response = self.request.put(self.url, self.body, app_code="wwc", pk=self.comment.pk)
        # print(response.json)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DestroyCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet


class ListCommentViewTestCase(APIBaseTestCase):
    view_class = CommentViewSet
