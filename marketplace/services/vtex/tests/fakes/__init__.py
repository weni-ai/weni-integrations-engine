"""
Reusable test doubles (Fakes) for VTEX integrations.

A Fake is a working in-memory implementation that honors the same contract as the
real collaborator (akin to an in-memory database). Inject `FakeVtexClient` wherever
a VTEX client is expected to exercise catalog sync/upload flows without hitting VTEX.
"""

from marketplace.services.vtex.tests.fakes.base import VtexFakeTestCase
from marketplace.services.vtex.tests.fakes.environment import VtexTestEnvironment
from marketplace.services.vtex.tests.fakes.facebook_client import (
    FakeFacebookCatalogClient,
)
from marketplace.services.vtex.tests.fakes.payloads import (
    build_order_form_simulation,
    build_sku_detail,
    normalize_simulation_item,
)
from marketplace.services.vtex.tests.fakes.vtex_client import FakeVtexClient


__all__ = [
    "FakeVtexClient",
    "FakeFacebookCatalogClient",
    "VtexTestEnvironment",
    "VtexFakeTestCase",
    "build_sku_detail",
    "build_order_form_simulation",
    "normalize_simulation_item",
]
