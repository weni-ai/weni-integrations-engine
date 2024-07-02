from typing import Protocol, Dict, Any


class RapidproClientProtocol(Protocol):  # pragma: no cover
    def send_alert(
        self, incident_name: str, monitor_name: str, details: Dict[str, Any]
    ) -> Any:
        pass
