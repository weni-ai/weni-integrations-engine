"""
Base TestCase for VTEX flows backed by in-memory fakes.

Provides an isolated LocMemCache (so tests never hit Redis) and a ready-to-use
`self.vtex` environment. Subclasses can override `build_environment` to customize
the fixtures.

Example:
    class MyUploadFlowTest(VtexFakeTestCase):
        def build_environment(self):
            return VtexTestEnvironment.create().add_product("1047", price=1500)

        def test_something(self):
            details = self.vtex.service.get_product_details("1047", self.vtex.domain)
            ...
"""

from django.core.cache import cache
from django.test import TestCase, override_settings

from marketplace.services.vtex.tests.fakes.environment import VtexTestEnvironment


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "vtex-fake-testcase",
        }
    }
)
class VtexFakeTestCase(TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        self.vtex = self.build_environment()

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def build_environment(self) -> VtexTestEnvironment:
        return VtexTestEnvironment.create()
