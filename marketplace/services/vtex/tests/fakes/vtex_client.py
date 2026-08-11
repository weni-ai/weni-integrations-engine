"""
In-memory Fake of the VTEX client.

`FakeVtexClient` implements the same surface as `VtexPrivateClient`/`VtexProxyClient`,
backed by an in-memory dataset of VTEX-shaped payloads. Inject it wherever a VTEX
client is expected (e.g. `PrivateProductsService(FakeVtexClient(...))`) to exercise
catalog sync/upload flows without performing real HTTP calls.

Example:
    client = (
        FakeVtexClient()
        .add_product("1047", sellers=["1"], available=True, price=1500)
        .add_product("2099", sellers=["1", "2"], available=False)
    )
    service = PrivateProductsService(client)
    details = service.get_product_details("1047", "store.myvtex.com")
"""

from typing import Any, Dict, List, Optional, Tuple

from marketplace.clients.exceptions import CustomAPIException
from marketplace.services.vtex.tests.fakes.payloads import (
    build_order_form_simulation,
    build_sku_detail,
    normalize_simulation_item,
)


class FakeVtexClient:
    def __init__(
        self, *, domain_valid: bool = True, credentials_valid: bool = True
    ) -> None:
        self.domain_valid = domain_valid
        self.credentials_valid = credentials_valid
        self._sellers: List[str] = []
        self._details: Dict[str, dict] = {}
        self._specs: Dict[str, Any] = {}
        self._items: Dict[Tuple[str, str, Optional[str]], dict] = {}
        # Spy: records every contract call as (method_name, kwargs).
        self.calls: List[Tuple[str, dict]] = []

    # ================================
    # Dataset registration (builder API)
    # ================================
    def add_seller(self, seller_id, *, active: bool = True) -> "FakeVtexClient":
        seller_id = str(seller_id)
        if active and seller_id not in self._sellers:
            self._sellers.append(seller_id)
        return self

    def add_product(
        self,
        sku_id,
        *,
        sellers: Optional[List[str]] = None,
        available: bool = True,
        price: int = 10000,
        list_price: Optional[int] = None,
        selling_price: Optional[int] = None,
        sales_channel: Optional[str] = None,
        specification: Any = None,
        **detail_overrides,
    ) -> "FakeVtexClient":
        """Register a product (SKU detail + per-seller cart availability)."""
        sku_id = str(sku_id)
        sellers = [str(seller) for seller in (sellers or ["1"])]
        self._details[sku_id] = build_sku_detail(
            sku_id, sellers=sellers, **detail_overrides
        )
        if specification is not None:
            self._specs[self._details[sku_id]["ProductId"]] = specification

        channel = str(sales_channel) if sales_channel is not None else None
        for seller in sellers:
            self.add_seller(seller)
            self._items[(sku_id, seller, channel)] = {
                "id": sku_id,
                "seller": seller,
                "available": available,
                "price": price,
                "list_price": list_price if list_price is not None else price,
                "selling_price": selling_price if selling_price is not None else price,
            }
        return self

    # ================================
    # Internal helpers
    # ================================
    def _record(self, method: str, **kwargs) -> None:
        self.calls.append((method, kwargs))

    def _lookup_item(self, sku_id, seller_id, channel) -> Optional[dict]:
        channel = str(channel) if channel is not None else None
        key = (str(sku_id), str(seller_id), channel)
        if key in self._items:
            return self._items[key]
        # Fall back to a channel-agnostic registration for ergonomics.
        return self._items.get((str(sku_id), str(seller_id), None))

    # ================================
    # VTEX client contract
    # ================================
    def check_domain(self, domain) -> bool:
        self._record("check_domain", domain=domain)
        return self.domain_valid

    def is_valid_credentials(self, domain) -> bool:
        self._record("is_valid_credentials", domain=domain)
        return self.credentials_valid

    def list_active_sellers(self, domain, sales_channel=None) -> List[str]:
        self._record("list_active_sellers", domain=domain, sales_channel=sales_channel)
        return list(self._sellers)

    def list_all_products_sku_ids(
        self, domain, page_size=100000, sales_channel=None
    ) -> List[str]:
        self._record(
            "list_all_products_sku_ids",
            domain=domain,
            page_size=page_size,
            sales_channel=sales_channel,
        )
        return list(self._details.keys())

    def get_product_details(self, sku_id, domain) -> Dict[str, Any]:
        self._record("get_product_details", sku_id=sku_id, domain=domain)
        details = self._details.get(str(sku_id))
        if details is None:
            raise CustomAPIException(detail=f"SKU {sku_id} not found", status_code=404)
        return details

    def get_product_specification(self, product_id, domain) -> Any:
        self._record("get_product_specification", product_id=product_id, domain=domain)
        return self._specs.get(str(product_id), [])

    def pub_simulate_cart_for_seller(
        self, sku_id, seller_id, domain, sales_channel=None
    ) -> Dict[str, Any]:
        self._record(
            "pub_simulate_cart_for_seller",
            sku_id=sku_id,
            seller_id=seller_id,
            domain=domain,
            sales_channel=sales_channel,
        )
        item = self._lookup_item(sku_id, seller_id, sales_channel)
        if item is None:
            return {"is_available": False, "price": 0, "list_price": 0}

        order_form = build_order_form_simulation([item])
        return normalize_simulation_item(order_form["items"][0], order_form)

    def simulate_cart_for_multiple_sellers(
        self, sku_id, sellers, domain, sales_channel=None
    ) -> Dict[str, Dict[str, Any]]:
        self._record(
            "simulate_cart_for_multiple_sellers",
            sku_id=sku_id,
            sellers=list(sellers),
            domain=domain,
            sales_channel=sales_channel,
        )
        raw_items = []
        for seller in sellers:
            item = self._lookup_item(sku_id, seller, sales_channel)
            if item is not None:
                raw_items.append(item)

        order_form = build_order_form_simulation(raw_items)
        return {
            raw["seller"]: normalize_simulation_item(raw, order_form)
            for raw in order_form["items"]
        }
