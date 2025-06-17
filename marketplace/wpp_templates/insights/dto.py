from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass(frozen=True)
class TemplateMetricsDTO:
    template_versions: List[str]
    start: date
    end: date
    app_uuid: str
