from django.test import TestCase

from marketplace.services.vtex.utils.facebook_product_dto import FacebookProductDTO


class TestFacebookProductDTO(TestCase):
    """Tests for FacebookProductDTO.to_meta_payload behavior and filtering."""

    def test_to_meta_payload_includes_only_allowed_and_truthy_fields(self):
        """Ensure only allowed fields are included and falsy values are removed."""
        dto = FacebookProductDTO(
            id="123",
            title="My Product",
            description="Desc",
            availability="in stock",
            status="Active",
            condition="new",
            price="",  # falsy -> should be removed
            link="https://example.com/p/123",
            image_link="https://example.com/i/123.jpg",
            brand="BrandX",
            sale_price="",  # falsy -> should be removed
            product_details={"anything": "ignored"},  # not allowed -> should be removed
            additional_image_link="",  # falsy -> should be removed
            rich_text_description="",  # falsy -> should be removed
        )

        payload = dto.to_meta_payload()

        # Required/allowed & truthy fields present
        self.assertEqual(payload["id"], "123")
        self.assertEqual(payload["title"], "My Product")
        self.assertEqual(payload["description"], "Desc")
        self.assertEqual(payload["availability"], "in stock")
        self.assertEqual(payload["status"], "Active")
        self.assertEqual(payload["condition"], "new")
        self.assertEqual(payload["link"], "https://example.com/p/123")
        self.assertEqual(payload["image_link"], "https://example.com/i/123.jpg")
        self.assertEqual(payload["brand"], "BrandX")

        # Falsy or disallowed fields removed
        self.assertNotIn("price", payload)
        self.assertNotIn("sale_price", payload)
        self.assertNotIn("product_details", payload)
        self.assertNotIn("additional_image_link", payload)
        self.assertNotIn("rich_text_description", payload)

    def test_to_meta_payload_includes_optional_when_truthy(self):
        """Ensure optional fields are included when provided as truthy values."""
        dto = FacebookProductDTO(
            id="1",
            title="T",
            description="D",
            availability="in stock",
            status="Active",
            condition="new",
            price="100.00",
            link="L",
            image_link="I",
            brand="B",
            sale_price="90.00",
            product_details={},
            additional_image_link="https://example.com/i/extra.jpg",
            rich_text_description="Rich text",
        )

        payload = dto.to_meta_payload()

        self.assertEqual(payload["price"], "100.00")
        self.assertEqual(payload["sale_price"], "90.00")
        self.assertEqual(
            payload["additional_image_link"], "https://example.com/i/extra.jpg"
        )
        self.assertEqual(payload["rich_text_description"], "Rich text")
