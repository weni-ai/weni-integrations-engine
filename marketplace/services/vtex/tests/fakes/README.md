# VTEX test fakes

Reusable **test doubles (Fakes)** for VTEX and Meta (Facebook) integrations.

A *Fake* is a lightweight, working in-memory implementation that honors the same
contract as the real collaborator (like an in-memory database). Inject these
wherever a real client/service is expected to exercise catalog **sync** and
**upload** flows **without performing any external HTTP call** (VTEX, Meta),
**Redis** or **broker**.

> Prefer this toolkit over ad-hoc `Mock()`/`patch` when writing tests for VTEX
> catalog, products, sync or upload flows.

## Components

| Symbol | Purpose |
|---|---|
| `FakeVtexClient` | In-memory client with the full `VtexPrivateClient`/`VtexProxyClient` contract (sellers, SKU ids, product details, cart simulation). Builder API + call spy. |
| `FakeFacebookCatalogClient` | In-memory Meta catalog client (`items_batch` + catalog lifecycle). Records uploaded batches/items. |
| `VtexTestEnvironment` | Creates the DB fixtures (vtex `App` + wpp-cloud `App` + linked `Catalog`) and wires a `FakeVtexClient` + real `PrivateProductsService`. |
| `VtexFakeTestCase` | Base `TestCase` with isolated `LocMemCache` and a ready-to-use `self.vtex` environment. |
| `build_sku_detail` / `build_order_form_simulation` / `normalize_simulation_item` | Builders for the raw VTEX payload shapes. |

All symbols are importable from the package root:

```python
from marketplace.services.vtex.tests.fakes import (
    FakeVtexClient,
    FakeFacebookCatalogClient,
    VtexTestEnvironment,
    VtexFakeTestCase,
    build_sku_detail,
)
```

## Quickstart

### 1. Base test case (recommended)

Subclass `VtexFakeTestCase` and declare your scenario in `build_environment`:

```python
from marketplace.services.vtex.tests.fakes import VtexFakeTestCase, VtexTestEnvironment


class MyCatalogFlowTest(VtexFakeTestCase):
    def build_environment(self) -> VtexTestEnvironment:
        return (
            VtexTestEnvironment.create(store_domain="www.mystore.com.br")
            .add_product("1047", price=1500, selling_price=1200, brand="Arado")
            .add_product("2099", available=False)
        )

    def test_fetches_product(self):
        details = self.vtex.service.get_product_details("1047", self.vtex.domain)
        self.assertEqual(details["Id"], "1047")
        # self.vtex.catalog / self.vtex.vtex_app / self.vtex.project_uuid available too
```

### 2. Standalone client (no DB needed)

```python
from marketplace.services.vtex.private.products.service import PrivateProductsService
from marketplace.services.vtex.tests.fakes import FakeVtexClient

client = FakeVtexClient().add_product("1047", sellers=["1"], price=1500)
service = PrivateProductsService(client)

# unknown SKU -> raises CustomAPIException(status_code=404)
# .calls records every contract call for spy-style assertions
```

### 3. Full pipeline through the real `DataProcessor`

Run the production extraction/validation pipeline against in-memory data
(`API_ONLY` returns DTOs without writing to the DB):

```python
from marketplace.services.vtex.utils.data_processor import DataProcessor
from marketplace.services.vtex.utils.enums import ProductPriority

results = DataProcessor(use_threads=False).process(
    items=["1047"],
    catalog=self.vtex.catalog,
    domain=self.vtex.domain,
    service=self.vtex.service,
    rules=[],
    store_domain=self.vtex.store_domain,
    mode="single",
    sellers=["1"],
    priority=ProductPriority.API_ONLY,
)
# results[0] is a faithful FacebookProductDTO
```

> The pipeline's `SKUValidator` touches Redis/cache. Under `VtexFakeTestCase`
> the cache is already a `LocMemCache`; patch the redis connection and
> `close_old_connections` for the few code paths that use them:
> ```python
> @patch("marketplace.services.vtex.utils.data_processor.close_old_connections")
> @patch("marketplace.services.vtex.utils.sku_validator.get_redis_connection", return_value=MagicMock())
> ```

### 4. Upload to Meta (Facebook)

```python
from marketplace.services.facebook.service import FacebookService
from marketplace.services.vtex.tests.fakes import FakeFacebookCatalogClient

fb = FakeFacebookCatalogClient()
FacebookService(fb).upload_batch("catalog-123", payload)

assert fb.uploaded_items          # flattened item `data` dicts
assert fb.calls[0][0] == "upload_items_batch"
```

To exercise the real upload task (`ProductBatchUploader`), swap the client class:

```python
from marketplace.wpp_products.utils import ProductBatchUploader

ProductBatchUploader.fb_client_class = FakeFacebookCatalogClient  # patch in the test
```

## Conventions & notes

- **Prices** follow the VTEX convention of **integer cents** (e.g. `1500` == 15.00).
- This package lives under `tests/` and is **omitted from coverage** by design.
- Keep the fakes **faithful**: when a real response shape changes, update the
  builders in `payloads.py` so every dependent test stays realistic.
- Extend the fakes by adding methods that mirror the real client contract and
  recording calls in `self.calls`; avoid adding behavior the real client lacks.
