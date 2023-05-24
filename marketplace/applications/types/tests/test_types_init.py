import os

from django.test import TestCase

from marketplace.applications import types


class TestWrongModuleImport(TestCase):
    """
    Tests if "_get_modules" will return any error when trying to import a file
    """

    file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "test_wrong_module.txt"
    )

    def setUp(self):
        super().setUp()

        with open(self.file_path, "w"):
            ...

    def tearDown(self):
        super().setUp()

        if os.path.exists(self.file_path):
            os.remove(self.file_path)

    def test_wrong_module_not_appars_on_get_modules(self):
        list(types._get_modules())
