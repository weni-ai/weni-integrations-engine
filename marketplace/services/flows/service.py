class FlowsService:
    def __init__(self, client):
        self.client = client

    def update_vtex_integration_status(self, project_uuid, user_email, action):
        return self.client.update_vtex_integration_status(
            project_uuid, user_email, action
        )
