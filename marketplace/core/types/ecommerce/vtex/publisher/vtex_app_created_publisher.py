from marketplace.event_driven.publishers import EDAPublisher


class VtexAppCreatedPublisher(EDAPublisher):
    exchange = "vtex_apps"
    routing_key = "vtex_apps.created"

    def create_event(self, data):
        return self.publish(data)
