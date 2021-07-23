from django.test import TestCase
from django.core.exceptions import ValidationError

from marketplace.core.validators import validate_app_code_exists


class ValidateAppCodeExistsTestCase(TestCase):
    def test_invalid_app_code(self):
        value = "wrong"
        with self.assertRaisesMessage(ValidationError, f"AppType ({value}) not exists!"):
            validate_app_code_exists(value)

    def test_valid_app_code(self):
        value = "wwc"
        validate_app_code_exists(value)
