import uuid

from django.test import TestCase
from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from marketplace.core.fields import Base64ImageField


class FakeSerializer(serializers.Serializer):
    image = Base64ImageField()


class Base64ImageFieldTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.data = dict(
            image="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeA"
            "AAAA3NCSVQICAjb4U/gAAAADElEQVQImWNgYGAAAAAEAAGjChXjAAAAAElFTkSuQmCC"
        )

    def test_invalid_data_header(self):
        self.data.update({"image": self.data["image"].replace("data:", "fakeheader")})
        serializer = FakeSerializer(data=self.data)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_invalid_base64_header(self):
        self.data.update({"image": self.data["image"].replace("base64,", "fakebase64")})
        serializer = FakeSerializer(data=self.data)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_invalid_base64_content(self):
        self.data.update({"image": self.data["image"].replace("base64,", "base64,fakebase64")})
        serializer = FakeSerializer(data=self.data)

        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_file_name(self):
        serializer = FakeSerializer(data=self.data)
        serializer.is_valid(raise_exception=True)

        content_file = serializer.validated_data["image"]

        self.assertTrue(isinstance(content_file, ContentFile))
        self.assertTrue(isinstance(content_file.file.read(), bytes))
        self.assertTrue(isinstance(content_file.name, str))
        self.assertTrue(content_file.name.endswith(".png"))
