from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class TemplateInsightsDTO:
    """
    Data Transfer Object for insight request parameters.
    """

    template_versions: List[str]
    start: datetime
    end: datetime
    app_uuid: str
