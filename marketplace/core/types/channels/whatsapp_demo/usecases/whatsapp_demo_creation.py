from marketplace.applications.models import App
from marketplace.clients.router.client import WPPRouterChannelClient


class EnsureWhatsAppDemoAppUseCase:
    def __init__(self, project_uuid: str, user):
        self.project_uuid = project_uuid
        self.user = user

    def get_or_create(self) -> App:
        # Importing here to resolve circular import issue
        from marketplace.core.types.channels.whatsapp_demo.type import WhatsAppDemoType

        app = App.objects.filter(
            code=WhatsAppDemoType.code,
            project_uuid=self.project_uuid,
        ).first()

        if app:
            return app

        app = WhatsAppDemoType().create_app(
            project_uuid=self.project_uuid,
            created_by=self.user,
        )

        # TODO: We should change this to use the FlowsClient in the future
        channel_token_client = WPPRouterChannelClient()

        return WhatsAppDemoType.configure_app(app, self.user, channel_token_client)
