from typing import Protocol, Dict, Any


class RapidproClientProtocol(Protocol):
    def send_alert(
        self, incident_name: str, monitor_name: str, details: Dict[str, Any]
    ) -> Any:
        pass
