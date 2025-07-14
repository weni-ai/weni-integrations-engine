from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SyncOnDemandDTO:
    """
    Data Transfer Object for syncing products on demand.
    """

    sku_ids: List[str]
    seller: str
    salles_channel: Optional[str]
