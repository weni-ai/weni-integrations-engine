"""Tests for the Account Verification serializers."""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from marketplace.core.types.channels.whatsapp_cloud.account_verification.serializers import (
    SubmitAccountVerificationSerializer,
)


class SubmitAccountVerificationSerializerTestCase(TestCase):
    def _pdf(self, name="doc.pdf", size=10):
        return SimpleUploadedFile(
            name, b"%PDF" + b"0" * (size - 4), content_type="application/pdf"
        )

    def test_accepts_a_single_pdf(self):
        serializer = SubmitAccountVerificationSerializer(
            data={"documents": [self._pdf()]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_accepts_up_to_three_documents(self):
        serializer = SubmitAccountVerificationSerializer(
            data={
                "documents": [
                    self._pdf(),
                    self._pdf(name="b.pdf"),
                    self._pdf(name="c.pdf"),
                ]
            }
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_rejects_more_than_three_documents(self):
        serializer = SubmitAccountVerificationSerializer(
            data={"documents": [self._pdf(name=f"{i}.pdf") for i in range(4)]}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("documents", serializer.errors)

    def test_rejects_empty_documents_list(self):
        serializer = SubmitAccountVerificationSerializer(data={"documents": []})
        self.assertFalse(serializer.is_valid())

    def test_rejects_unsupported_content_type(self):
        bad = SimpleUploadedFile("bad.gif", b"GIF89a", content_type="image/gif")
        serializer = SubmitAccountVerificationSerializer(data={"documents": [bad]})
        self.assertFalse(serializer.is_valid())
        self.assertIn("documents", serializer.errors)

    def test_rejects_oversized_document(self):
        big = SimpleUploadedFile(
            "big.pdf",
            b"%PDF" + b"0" * (5 * 1024 * 1024 + 1),
            content_type="application/pdf",
        )
        serializer = SubmitAccountVerificationSerializer(data={"documents": [big]})
        self.assertFalse(serializer.is_valid())

    def test_accepts_jpeg_and_png(self):
        jpeg = SimpleUploadedFile("a.jpg", b"\xff\xd8\xff", content_type="image/jpeg")
        png = SimpleUploadedFile(
            "a.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"
        )
        serializer = SubmitAccountVerificationSerializer(
            data={"documents": [jpeg, png]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
