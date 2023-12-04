class FlowsService:
    def __init__(self, client):
        self.client = client

    def notify_vtex_app_creation(self, project_uuid, user_email):
        return self.client.notify_vtex_app_creation(project_uuid, user_email)
