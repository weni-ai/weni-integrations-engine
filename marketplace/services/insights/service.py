class InsightsService:
    def __init__(self, client):
        self.client = client
    
    def get_whatsapp_data_integration(self, whatsapp_data):
        return self.client.create_whatsapp_integration(whatsapp_data)
