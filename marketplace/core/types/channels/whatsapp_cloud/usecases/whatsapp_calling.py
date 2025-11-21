from typing import Optional, Dict, Any

from marketplace.applications.models import App
from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import CallingService


class WhatsAppCallingUseCase:
    """
    Use case for reading and toggling WhatsApp Calling settings via Cloud API.
    """

    def __init__(self, app: App, calling_service: Optional[CallingService] = None):
        self.app = app
        if calling_service is not None:
            self._service = calling_service
        else:
            access_token = app.apptype.get_access_token(app)
            if not access_token:
                raise ValueError("This app does not have fb_access_token in settings")

            phone_number_id = app.config.get("wa_phone_number_id")
            if not phone_number_id:
                raise ValueError("The phone number is not configured")

            client = FacebookClient(access_token).get_calling_requests(phone_number_id)
            self._service = CallingService(client=client)

    def get_settings(self) -> Dict[str, Any]:
        """
        Fetch current calling settings from Meta Graph API.
        """
        return self._service.get_settings()

    def enable(self) -> Dict[str, Any]:
        """
        Enable WhatsApp Calling without configuring call_hours.
        If already enabled on Meta, it only persists local flags.
        """
        # 1) Read current settings
        current_settings = self._service.get_settings() or {}
        current_calling = current_settings.get("calling", {}) or {}
        current_status = current_calling.get("status")

        if current_status == "ENABLED":
            # Already enabled: just persist current info
            call_hours = current_calling.get("call_hours")
            self.app.config["has_calling"] = True
            self.app.config["calling_hours"] = call_hours
            self.app.save()
            return {
                "status": "ENABLED",
                "already_enabled": True,
                "calling_hours": call_hours,
                "settings": current_settings,
            }

        # 2) Not enabled: enable now
        self._service.enable()

        # 3) Read fresh settings and persist
        latest_settings = self._service.get_settings() or {}
        calling_config = latest_settings.get("calling", {}) or {}
        call_hours = calling_config.get("call_hours")

        self.app.config["has_calling"] = True
        self.app.config["calling_hours"] = call_hours
        self.app.save()

        return {
            "status": "ENABLED",
            "already_enabled": False,
            "calling_hours": call_hours,
            "settings": latest_settings,
        }

    def disable(self) -> Dict[str, Any]:
        """
        Disable WhatsApp Calling.
        """
        self._service.disable()
        latest_settings = self._service.get_settings() or {}
        # Persist flag on App config for frontend awareness
        self.app.config["has_calling"] = False
        self.app.config["calling_hours"] = None
        self.app.save()
        return {
            "status": "DISABLED",
            "settings": latest_settings,
            "calling_hours": None,
        }
