from marketplace.event_driven.publishers import EDAPublisher


class VtexAppCreatedPublisher(EDAPublisher):
    exchange = "create_vtex_app.topic"

    def create_event(self, data):
        return self.publish(data)
