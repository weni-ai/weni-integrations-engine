import json

from django.test import TestCase, override_settings

from unittest import mock

from marketplace.event_driven.publishers import (
    JsonContentType,
    GenericContentType,
    ContentTypeFactory,
    EDAPublisher,
    publish_event,
)


class ContentTypesTestCase(TestCase):
    def test_json_content_type_parse(self):
        data = {"key": "value", "number": 123}
        result = JsonContentType.parse(data)
        self.assertEqual(json.loads(result), data)

    def test_generic_content_type_parse_string(self):
        data = "Hello World"
        result = GenericContentType.parse(data)
        self.assertEqual(result, b"Hello World")

    def test_generic_content_type_parse_bytes(self):
        data = b"Hello World"
        result = GenericContentType.parse(data)
        self.assertEqual(result, b"b'Hello World'")


class ContentTypeFactoryTestCase(TestCase):
    def test_get_content_type_json(self):
        content_type = ContentTypeFactory.get_content_type("application/json")
        self.assertIsInstance(content_type, JsonContentType)

    def test_get_content_type_text(self):
        content_type = ContentTypeFactory.get_content_type("text")
        self.assertIsInstance(content_type, GenericContentType)


class ConcretePublisher(EDAPublisher):
    exchange = "test-exchange"
    routing_key = "test-routing-key"

    def create_event(self, *args, **kwargs):
        return self.publish({"event": "data"})


class EDAPublisherTestCase(TestCase):
    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_init_with_eda_enabled(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_backend = mock.MagicMock()
            mock_import_string.return_value = lambda: mock_backend

            publisher = ConcretePublisher()

            self.assertTrue(publisher.is_eda_enabled)
            self.assertEqual(publisher.backend, mock_backend)
            self.assertEqual(
                publisher.connection_params,
                {
                    "host": "localhost",
                    "port": 5672,
                    "userid": "guest",
                    "password": "guest",
                    "virtual_host": "/",
                },
            )
            mock_import_string.assert_called_once_with("path.to.backend")

    @override_settings(USE_EDA=False)
    def test_init_with_eda_disabled(self):
        publisher = ConcretePublisher()
        self.assertFalse(publisher.is_eda_enabled)

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_with_eda_enabled(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_backend = mock.MagicMock()
            mock_backend.publish.return_value = True
            mock_import_string.return_value = lambda: mock_backend

            publisher = ConcretePublisher()
            data = {"test": "data"}

            with mock.patch(
                "marketplace.event_driven.publishers.message_published.send"
            ) as mock_signal:
                result = publisher.publish(data)

                self.assertTrue(result)
                mock_backend.publish.assert_called_once_with(
                    connection_params=publisher.connection_params,
                    exchange="test-exchange",
                    routing_key="test-routing-key",
                    message=mock.ANY,
                    properties={"content_type": "application/json"},
                )
                mock_signal.assert_called_once_with(
                    sender=ConcretePublisher, data=data, routing_key="test-routing-key"
                )

    @override_settings(USE_EDA=False)
    def test_publish_with_eda_disabled(self):
        publisher = ConcretePublisher()
        data = {"test": "data"}
        result = publisher.publish(data)
        self.assertTrue(result)

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_with_custom_routing_key(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_backend = mock.MagicMock()
            mock_backend.publish.return_value = True
            mock_import_string.return_value = lambda: mock_backend

            publisher = ConcretePublisher()
            data = {"test": "data"}
            custom_routing_key = "custom-routing-key"

            result = publisher.publish(data, routing_key=custom_routing_key)

            self.assertTrue(result)
            mock_backend.publish.assert_called_once_with(
                connection_params=publisher.connection_params,
                exchange="test-exchange",
                routing_key=custom_routing_key,
                message=mock.ANY,
                properties={"content_type": "application/json"},
            )

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_with_custom_properties(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_backend = mock.MagicMock()
            mock_backend.publish.return_value = True
            mock_import_string.return_value = lambda: mock_backend

            publisher = ConcretePublisher()
            data = {"test": "data"}
            custom_properties = {"app_id": "test-app", "priority": 5}

            result = publisher.publish(data, properties=custom_properties)

            self.assertTrue(result)
            expected_properties = {
                "content_type": "application/json",
                "app_id": "test-app",
                "priority": 5,
            }
            mock_backend.publish.assert_called_once_with(
                connection_params=publisher.connection_params,
                exchange="test-exchange",
                routing_key="test-routing-key",
                message=mock.ANY,
                properties=expected_properties,
            )

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_with_custom_content_type(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_backend = mock.MagicMock()
            mock_backend.publish.return_value = True
            mock_import_string.return_value = lambda: mock_backend

            publisher = ConcretePublisher()
            publisher.content_type = "text"
            data = "Hello World"

            result = publisher.publish(data)

            self.assertTrue(result)
            mock_backend.publish.assert_called_once_with(
                connection_params=publisher.connection_params,
                exchange="test-exchange",
                routing_key="test-routing-key",
                message=b"Hello World",
                properties={"content_type": "text"},
            )


class PublishEventTestCase(TestCase):
    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_event_valid_publisher(self):
        mock_backend = mock.MagicMock()

        def side_effect(arg):
            if arg == "path.to.ConcretePublisher":
                return ConcretePublisher
            elif arg == "path.to.backend":
                return lambda: mock_backend
            return None

        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_import_string.side_effect = side_effect

            data = {"test": "data"}

            with mock.patch.object(
                ConcretePublisher, "publish", return_value=True
            ) as mock_publish:
                result = publish_event("path.to.ConcretePublisher", data)

                self.assertTrue(result)
                mock_import_string.assert_any_call("path.to.ConcretePublisher")
                mock_publish.assert_called_once_with(data, None, None)

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_event_invalid_publisher(self):
        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:

            class InvalidPublisher:
                pass

            mock_import_string.return_value = InvalidPublisher
            data = {"test": "data"}

            with self.assertRaises(ValueError) as context:
                publish_event("path.to.InvalidPublisher", data)

            self.assertIn("is not a valid EDAPublisher", str(context.exception))

    @override_settings(
        USE_EDA=True,
        EDA_CONNECTION_BACKEND="path.to.backend",
        EDA_BROKER_HOST="localhost",
        EDA_BROKER_PORT=5672,
        EDA_BROKER_USER="guest",
        EDA_BROKER_PASSWORD="guest",
        EDA_VIRTUAL_HOST="/",
    )
    def test_publish_event_with_custom_params(self):
        mock_backend = mock.MagicMock()

        def side_effect(arg):
            if arg == "path.to.ConcretePublisher":
                return ConcretePublisher
            elif arg == "path.to.backend":
                return lambda: mock_backend
            return None

        with mock.patch(
            "marketplace.event_driven.publishers.import_string"
        ) as mock_import_string:
            mock_import_string.side_effect = side_effect

            data = {"test": "data"}
            routing_key = "custom-key"
            properties = {"priority": 5}

            with mock.patch.object(
                ConcretePublisher, "publish", return_value=True
            ) as mock_publish:
                result = publish_event(
                    "path.to.ConcretePublisher", data, routing_key, properties
                )

                self.assertTrue(result)
                mock_publish.assert_called_once_with(data, routing_key, properties)
