import time

import amqp


class PyAMQPConnectionBackend:
    _start_message = "Waiting Events"

    def __init__(self, handle_consumers: callable):
        self._handle_consumers = handle_consumers

    def _drain_events(self, connection: amqp.connection.Connection):
        while True:
            try:
                connection.drain_events()
            except amqp.exceptions.AMQPError as error:
                raise error
            except Exception as error:
                # TODO: Handle exceptions with RabbitMQ
                print("error on drain_events:", type(error), error)

    def start_consuming(self, connection_params: dict):
        while True:
            try:
                with amqp.Connection(**connection_params) as connection:
                    channel = connection.channel()

                    self._handle_consumers(channel)

                    print(self._start_message)

                    self._drain_events(connection)

            except (amqp.exceptions.AMQPError, ConnectionRefusedError) as error:
                print(f"Connection error: {error}")
                time.sleep(5)
