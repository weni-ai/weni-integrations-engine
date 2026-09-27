from django.test import TestCase, override_settings

from marketplace.core.types.ecommerce.vtex.serializers import (
    UploadInlineProductsSerializer,
)


def _build_product(**overrides):
    product = {
        "id": "1047#1",
        "title": "Laranja Bahia Importada - Saco (15Kg)",
        "description": "Laranja Bahia Importada - Saco (15Kg)",
        "availability": "in stock",
        "status": "active",
        "condition": "new",
        "price": "10.00 BRL",
        "link": "https://www.arado.com.br/laranja-bahia-importada-1/p?idsku=1047",
        "image_link": "https://arado.vteximg.com.br/arquivos/ids/158691/img.jpg",
        "brand": "Arado",
        "sale_price": "8.00 BRL",
        "additional_image_link": "",
        "rich_text_description": "",
    }
    product.update(overrides)
    return product


class UploadInlineProductsSerializerTest(TestCase):
    def test_valid_payload(self):
        serializer = UploadInlineProductsSerializer(
            data={"products": [_build_product()]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(len(serializer.validated_data["products"]), 1)

    def test_optional_fields_default_to_empty_string(self):
        minimal_product = {
            "id": "55#1",
            "title": "Minimal",
            "description": "desc",
            "availability": "out of stock",
            "status": "active",
            "condition": "new",
            "link": "https://example.com/p",
            "image_link": "https://example.com/img.jpg",
            "brand": "Arado",
        }
        serializer = UploadInlineProductsSerializer(
            data={"products": [minimal_product]}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        product = serializer.validated_data["products"][0]
        self.assertEqual(product["price"], "")
        self.assertEqual(product["sale_price"], "")
        self.assertEqual(product["additional_image_link"], "")
        self.assertEqual(product["rich_text_description"], "")

    def test_empty_products_list_is_invalid(self):
        serializer = UploadInlineProductsSerializer(data={"products": []})
        self.assertFalse(serializer.is_valid())
        self.assertIn("products", serializer.errors)

    def test_missing_required_field_is_invalid(self):
        for field in (
            "id",
            "title",
            "description",
            "availability",
            "status",
            "condition",
            "link",
            "image_link",
            "brand",
        ):
            product = _build_product()
            product.pop(field)
            serializer = UploadInlineProductsSerializer(data={"products": [product]})
            self.assertFalse(
                serializer.is_valid(),
                f"Expected payload missing '{field}' to be invalid",
            )
            self.assertIn("products", serializer.errors)

    def test_blank_required_field_is_invalid(self):
        product = _build_product(brand="")
        serializer = UploadInlineProductsSerializer(data={"products": [product]})
        self.assertFalse(serializer.is_valid())
        self.assertIn("products", serializer.errors)

    def test_in_stock_without_price_is_invalid(self):
        product = _build_product(availability="in stock", price="")
        serializer = UploadInlineProductsSerializer(data={"products": [product]})
        self.assertFalse(serializer.is_valid())
        self.assertIn("products", serializer.errors)

    def test_out_of_stock_without_price_is_valid(self):
        product = _build_product(availability="out of stock", price="")
        serializer = UploadInlineProductsSerializer(data={"products": [product]})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    @override_settings(VTEX_UPLOAD_PRODUCTS_MAX_BATCH=2)
    def test_exceeding_max_batch_is_invalid(self):
        products = [_build_product(id=f"{i}#1") for i in range(3)]
        serializer = UploadInlineProductsSerializer(data={"products": products})
        self.assertFalse(serializer.is_valid())
        self.assertIn("products", serializer.errors)
