import json

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, AnyStr, Literal

from django.conf import settings
from django.utils.module_loading import import_string

from .signals import message_published


class ContentTypeInterface(Protocol):
    def parse(data: Any) -> Any:
        ...


class JsonContentType(ContentTypeInterface):
    @staticmethod
    def parse(data: Dict[str, Any]) -> bytes:
        return json.dumps(data).encode("utf-8")


class GenericContentType(ContentTypeInterface):
    @staticmethod
    def parse(data: AnyStr) -> bytes:
        return str(data).encode("utf-8")


class ContentTypeFactory:
    @staticmethod
    def get_content_type(name: Literal["application/json", "text"]):
        if name == "application/json":
            return JsonContentType()
        elif name == "text":
            return GenericContentType()


class EDAPublisher(ABC):
    """
    Publisher's base class.
    """

    exchange: str = ""
    routing_key: str = ""
    content_type: str = "application/json"

    def __init__(self):
        self.is_eda_enabled = getattr(settings, "USE_EDA", False)

        if self.is_eda_enabled:
            self.backend = import_string(settings.EDA_CONNECTION_BACKEND)()
            self.connection_params = dict(
                host=settings.EDA_BROKER_HOST,
                port=settings.EDA_BROKER_PORT,
                userid=settings.EDA_BROKER_USER,
                password=settings.EDA_BROKER_PASSWORD,
                virtual_host=settings.EDA_VIRTUAL_HOST,
            )

    def publish(
        self,
        data: Any,
        routing_key: Optional[str] = None,
        properties: Optional[Dict] = None,
    ) -> bool:
        """
        Publishes as event into broker.

        Args:
            data: Data to publish
            routing_key: Routing key (opcional)
            properties: Extra properties of message

        Returns:
            bool
        """
        if not self.is_eda_enabled:
            return True

        if routing_key is None:
            routing_key = self.routing_key

        if properties is None:
            properties = {}

        if "content_type" not in properties:
            properties["content_type"] = self.content_type

        message = ContentTypeFactory.get_content_type(self.content_type).parse(data)

        result = self.backend.publish(
            connection_params=self.connection_params,
            exchange=self.exchange,
            routing_key=routing_key,
            message=message,
            properties=properties,
        )

        if result:
            message_published.send(
                sender=self.__class__, data=data, routing_key=routing_key
            )

        return result

    @abstractmethod
    def create_event(self, *args, **kwargs) -> bool:
        """
        Abstract method to contain logic of an event to be published
        """
        pass


def publish_event(
    publisher_class: str,
    data: Any,
    routing_key: Optional[str] = None,
    properties: Optional[Dict] = None,
) -> bool:
    """
    Simplified function to publish events.

    Args:
        publisher_class: Path to the publisher class
        data: Data to be published
        routing_key: Routing key (optional)
        properties: Extra properties of message (optional)

    Returns:
        bool
    """
    publisher_cls = import_string(publisher_class)
    if not issubclass(publisher_cls, EDAPublisher):
        raise ValueError(f"{publisher_class} is not a valid EDAPublisher")

    publisher = publisher_cls()
    return publisher.publish(data, routing_key, properties)
