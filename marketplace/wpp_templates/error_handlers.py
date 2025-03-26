import logging

from datetime import datetime

from marketplace.applications.models import App


"""
Error handling utilities for WhatsApp templates.
This module provides functions to handle errors related to WhatsApp templates
and update application configurations accordingly.
"""

logger = logging.getLogger(__name__)


def handle_error_and_update_config(app: App, error_data):
    """
    Handle specific errors and update app configuration to prevent future sync attempts.

    This function checks for specific error codes (100 with subcode 33) that indicate
    persistent issues with Meta synchronization. When these errors are detected,
    the app configuration is updated to ignore future sync attempts.

    Args:
        app (App): The application instance to update
        error_data (dict): Error information containing code, subcode, and message

    Returns:
        None
    """
    error_code = error_data.get("code")
    error_subcode = error_data.get("error_subcode")

    if error_code == 100 and error_subcode == 33:
        app.config["ignores_meta_sync"] = {
            "last_error_date": datetime.now().isoformat(),
            "last_error_message": error_data.get("message"),
            "code": error_code,
            "error_subcode": error_subcode,
        }
        app.save()

        logger.info(
            f"Config updated to ignore future syncs for app {app.uuid} due to persistent errors."
        )
