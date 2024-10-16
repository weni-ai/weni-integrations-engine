from rest_framework.exceptions import NotFound

from django.core.exceptions import ObjectDoesNotExist

from marketplace.applications.models import App


class VtexIntegration:
    @staticmethod
    def vtex_integration_detail(project_uuid):
        """
        Fetches the VTEX app for a given project UUID and returns API credentials.
        Raises a NotFound exception if the app does not exist.
        """
        try:
            vtex_app = App.objects.get(code="vtex", project_uuid=project_uuid)
            return VtexIntegration.get_api_credentials(vtex_app)
        except ObjectDoesNotExist:
            raise NotFound(
                detail="A vtex-app integration was not found for the provided project UUID."
            )

    @staticmethod
    def get_api_credentials(vtex_app):
        """
        Extracts API credentials from the app's config and ensures the domain has https.
        """
        config = vtex_app.config.get("api_credentials", {})

        api_credentials = {
            "app_key": config.get("app_key"),
            "app_token": config.get("app_token"),
            "domain": VtexIntegration.ensure_https(config.get("domain")),
        }

        return api_credentials

    @staticmethod
    def ensure_https(domain):
        """
        Ensures that the domain starts with 'https://'. Adds it if missing.
        """
        if domain and not domain.startswith("https://"):
            return f"https://{domain}"
        return domain
