"""
In-memory Fake for the Meta (Facebook) Catalog client.

`FakeFacebookCatalogClient` implements the catalog/upload surface used by the
product upload flow, recording uploaded batches and returning realistic
responses. Use it to test upload-to-Meta flows without performing real HTTP calls.

Wiring into the upload pipeline:
    from marketplace.wpp_products.utils import ProductBatchUploader
    ProductBatchUploader.fb_client_class = FakeFacebookCatalogClient

or, at the service level:
    FacebookService(FakeFacebookCatalogClient())
"""

from typing import Any, Dict, List, Optional, Tuple


class FakeFacebookCatalogClient:
    def __init__(self, access_token: Optional[str] = None) -> None:
        self.access_token = access_token
        self.uploaded_batches: List[Dict[str, Any]] = []
        # Spy: records every call as (method_name, kwargs).
        self.calls: List[Tuple[str, dict]] = []

    def _record(self, method: str, **kwargs) -> None:
        self.calls.append((method, kwargs))

    def upload_items_batch(self, catalog_id, payload) -> Dict[str, Any]:
        """Mirror Meta `/{catalog_id}/items_batch`, returning handles on success."""
        self._record("upload_items_batch", catalog_id=catalog_id, payload=payload)
        self.uploaded_batches.append({"catalog_id": catalog_id, "payload": payload})
        requests = payload.get("requests", [])
        return {
            "handles": [
                f"handle-{catalog_id}-{index}" for index in range(len(requests))
            ]
        }

    @property
    def uploaded_items(self) -> List[Dict[str, Any]]:
        """Flatten the item `data` dicts across every uploaded batch."""
        items: List[Dict[str, Any]] = []
        for batch in self.uploaded_batches:
            for request in batch["payload"].get("requests", []):
                items.append(request.get("data", {}))
        return items

    # ================================
    # Catalog lifecycle (minimal; extend as flows require)
    # ================================
    def create_catalog(self, business_id, name) -> Dict[str, Any]:
        self._record("create_catalog", business_id=business_id, name=name)
        return {"id": "fake-catalog-id"}

    def destroy_catalog(self, catalog_id) -> bool:
        self._record("destroy_catalog", catalog_id=catalog_id)
        return True

    def enable_catalog(self, waba_id, catalog_id) -> Dict[str, Any]:
        self._record("enable_catalog", waba_id=waba_id, catalog_id=catalog_id)
        return {"success": True}

    def disable_catalog(self, waba_id, catalog_id) -> Dict[str, Any]:
        self._record("disable_catalog", waba_id=waba_id, catalog_id=catalog_id)
        return {"success": True}

    def get_connected_catalog(self, waba_id) -> Dict[str, Any]:
        self._record("get_connected_catalog", waba_id=waba_id)
        return {"data": []}
