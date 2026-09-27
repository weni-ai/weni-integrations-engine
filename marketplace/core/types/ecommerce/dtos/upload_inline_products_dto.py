from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class UploadInlineProductsDTO:
    """
    Carries pre-formatted (and possibly edited) products to be uploaded to Meta.

    The products follow the same shape returned by the inline sync endpoint, so each
    item already holds Meta-ready fields and a unified `id` ("sku#seller").
    """

    products: List[Dict[str, str]]
