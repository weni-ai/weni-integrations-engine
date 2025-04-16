import time

import amqp

import logging

logger = logging.getLogger(__name__)


class PyAMQPConnectionBackend:  # pragma: no cover
    _start_message = "[+] Connection established. Waiting for events"

    def __init__(self, handle_consumers: callable = None):
        self._handle_consumers = handle_consumers

    def _drain_events(self, connection: amqp.connection.Connection):
        while True:
            connection.drain_events()

    def start_consuming(self, connection_params: dict):
        while True:
            try:
                with amqp.Connection(**connection_params) as connection:
                    channel = connection.channel()

                    self._handle_consumers(channel)

                    print(self._start_message)

                    self._drain_events(connection)

            except (
                amqp.exceptions.AMQPError,
                ConnectionRefusedError,
                OSError,
            ) as error:
                print(f"[-] Connection error: {error}")
                print("    [+] Reconnecting in 5 seconds...")
                time.sleep(5)

            except Exception as error:
                # TODO: Handle exceptions with RabbitMQ
                print("error on drain_events:", type(error), error)
                time.sleep(5)

    def publish(
        self,
        connection_params: dict,
        exchange: str,
        routing_key: str,
        message: bytes,
        properties: dict = None,
    ):
        """
        Publishes a message in AMQP broker.

        Args:
            connection_params: Broker connections params
            exchange: Exchange's name
            routing_key: Routing key
            message: Message content (bytes)
            properties: Extra properties (dict)

        Returns:
            bool
        """
        if properties is None:
            properties = {}

        try:
            with amqp.Connection(**connection_params) as connection:
                channel = connection.channel()

                msg = amqp.Message(body=message, **properties)

                channel.basic_publish(msg, exchange=exchange, routing_key=routing_key)

                return True
        except (amqp.exceptions.AMQPError, ConnectionRefusedError, OSError) as error:
            logger.error(f"[-] Error publishing message: {error}")
            return False
