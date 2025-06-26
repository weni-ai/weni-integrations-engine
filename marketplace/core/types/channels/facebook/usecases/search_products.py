import json

from typing import Any, List, Sequence

from marketplace.services.facebook.service import FacebookService


class FacebookSearchProductsUseCase:
    """Coordinates a Facebook catalog search for a given catalog ID."""

    def __init__(self, service: FacebookService) -> None:
        """Inject a concrete FacebookService instance."""
        self._service = service

    def execute(
        self,
        catalog_id: str,
        product_ids: List[str],
        fields: List[str],
        summary: bool = False,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Run the search and return the raw Graph-API payload."""
        fields_str = self._prepare_fields(fields)
        filter_str = self._build_filter(product_ids)

        return self._service.get_product_by_catalog_id(
            catalog_id=catalog_id,
            filter_str=filter_str,
            fields_str=fields_str,
            summary=summary,
            limit=limit,
        )

    # ------------------------------------------------------------------ #
    # Internal helpers (business rules)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _prepare_fields(fields: List[str]) -> str:
        """Ensure mandatory fields and return a comma-separated string."""
        base_fields = list(fields) if fields else ["id", "name"]
        if "retailer_id" not in base_fields:
            base_fields.append("retailer_id")
        return ",".join(base_fields)

    @staticmethod
    def _build_filter(product_ids: Sequence[str]) -> str:
        """Return the JSON filter expected by the Catalog API."""
        filter_meta = {
            "or": [
                {
                    "and": [
                        {"retailer_id": {"i_contains": rid}},
                        {"availability": {"i_contains": "in stock"}},
                        {"visibility": {"i_contains": "published"}},
                    ]
                }
                for rid in product_ids
            ]
        }
        return json.dumps(filter_meta, separators=(",", ":"))
