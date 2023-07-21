import amqp


class PyAMQPConnectionBackend:
    _start_message = "Waiting Events"

    def __init__(self, handle_consumers: callable):
        self._handle_consumers = handle_consumers

    def start_consuming(self, connection_params: dict):
        with amqp.Connection(**connection_params) as connection:
            channel = connection.channel()

            self._handle_consumers(channel)

            print(self._start_message)

            while True:
                try:
                    connection.drain_events()
                except Exception as error:
                    print(error)
