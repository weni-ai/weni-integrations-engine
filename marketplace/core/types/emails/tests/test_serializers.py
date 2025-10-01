import unittest

from marketplace.core.types.emails.base_serializer import BaseEmailSerializer


class BaseEmailSerializerTestCase(unittest.TestCase):
    """Test cases for BaseEmailSerializer validation methods"""

    def setUp(self):
        self.valid_data = {
            "username": "test@example.com",
            "password": "password123",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "imap_host": "imap.example.com",
            "imap_port": 993,
        }

    def test_valid_data_passes_validation(self):
        """Test that valid data passes all validations"""
        serializer = BaseEmailSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

    def test_smtp_port_validation_valid_ports(self):
        """Test SMTP port validation with valid ports"""
        valid_ports = [465, 587]

        for port in valid_ports:
            with self.subTest(port=port):
                data = self.valid_data.copy()
                data["smtp_port"] = port
                serializer = BaseEmailSerializer(data=data)
                self.assertTrue(serializer.is_valid())

    def test_smtp_port_validation_invalid_ports(self):
        """Test SMTP port validation with invalid ports"""
        invalid_ports = [25, 80, 443, 8080, 0, -1]

        for port in invalid_ports:
            with self.subTest(port=port):
                data = self.valid_data.copy()
                data["smtp_port"] = port
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("smtp_port", serializer.errors)
                self.assertEqual(
                    serializer.errors["smtp_port"][0],
                    "SMTP port must be 465 (SSL) or 587 (TLS).",
                )

    def test_imap_port_validation_valid_ports(self):
        """Test IMAP port validation with valid ports"""
        valid_ports = [993, 143]

        for port in valid_ports:
            with self.subTest(port=port):
                data = self.valid_data.copy()
                data["imap_port"] = port
                serializer = BaseEmailSerializer(data=data)
                self.assertTrue(serializer.is_valid())

    def test_imap_port_validation_invalid_ports(self):
        """Test IMAP port validation with invalid ports"""
        invalid_ports = [25, 80, 443, 587, 465, 8080, 0, -1]

        for port in invalid_ports:
            with self.subTest(port=port):
                data = self.valid_data.copy()
                data["imap_port"] = port
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("imap_port", serializer.errors)
                self.assertEqual(
                    serializer.errors["imap_port"][0],
                    "IMAP port must be 993 (SSL/TLS) or 143.",
                )

    def test_smtp_host_validation_valid_hosts(self):
        """Test SMTP host validation with valid hosts"""
        valid_hosts = [
            "smtp.gmail.com",
            "smtp.example.com",
            "mail.server.org",
            "smtp-1.company.net",
            "smtp.mail-provider.co.uk",
        ]

        for host in valid_hosts:
            with self.subTest(host=host):
                data = self.valid_data.copy()
                data["smtp_host"] = host
                serializer = BaseEmailSerializer(data=data)
                self.assertTrue(serializer.is_valid())

    def test_smtp_host_validation_invalid_hosts(self):
        """Test SMTP host validation with invalid hosts"""
        invalid_hosts = [
            "invalid-host",
            "smtp@example.com",
            "smtp_example.com",
            "smtp example.com",
            "smtp.example.c",
            "smtp.example.com:587",
            "http://smtp.example.com",
        ]

        for host in invalid_hosts:
            with self.subTest(host=host):
                data = self.valid_data.copy()
                data["smtp_host"] = host
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("smtp_host", serializer.errors)
                self.assertEqual(
                    serializer.errors["smtp_host"][0], "Invalid SMTP host format."
                )

    def test_smtp_host_validation_empty_host(self):
        """Test SMTP host validation with empty host"""
        data = self.valid_data.copy()
        data["smtp_host"] = ""
        serializer = BaseEmailSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("smtp_host", serializer.errors)
        self.assertEqual(
            serializer.errors["smtp_host"][0], "This field may not be blank."
        )

    def test_imap_host_validation_valid_hosts(self):
        """Test IMAP host validation with valid hosts"""
        valid_hosts = [
            "imap.gmail.com",
            "imap.example.com",
            "mail.server.org",
            "imap-1.company.net",
            "imap.mail-provider.co.uk",
        ]

        for host in valid_hosts:
            with self.subTest(host=host):
                data = self.valid_data.copy()
                data["imap_host"] = host
                serializer = BaseEmailSerializer(data=data)
                self.assertTrue(serializer.is_valid())

    def test_imap_host_validation_invalid_hosts(self):
        """Test IMAP host validation with invalid hosts"""
        invalid_hosts = [
            "invalid-host",
            "imap@example.com",
            "imap_example.com",
            "imap example.com",
            "imap.example.c",
            "imap.example.com:993",
            "http://imap.example.com",
        ]

        for host in invalid_hosts:
            with self.subTest(host=host):
                data = self.valid_data.copy()
                data["imap_host"] = host
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("imap_host", serializer.errors)
                self.assertEqual(
                    serializer.errors["imap_host"][0], "Invalid IMAP host format."
                )

    def test_imap_host_validation_empty_host(self):
        """Test IMAP host validation with empty host"""
        data = self.valid_data.copy()
        data["imap_host"] = ""
        serializer = BaseEmailSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("imap_host", serializer.errors)
        self.assertEqual(
            serializer.errors["imap_host"][0], "This field may not be blank."
        )

    def test_to_channel_data_method(self):
        """Test to_channel_data method returns correct data structure"""
        serializer = BaseEmailSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())

        result = serializer.to_channel_data()

        expected = {
            "username": "test@example.com",
            "password": "password123",
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "imap_host": "imap.example.com",
            "imap_port": 993,
        }

        self.assertEqual(result, expected)

    def test_required_fields_validation(self):
        """Test that all required fields are properly validated"""
        required_fields = [
            "username",
            "password",
            "smtp_host",
            "smtp_port",
            "imap_host",
            "imap_port",
        ]

        for field in required_fields:
            with self.subTest(field=field):
                data = self.valid_data.copy()
                del data[field]
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_username_email_validation(self):
        """Test username field accepts only valid email addresses"""
        invalid_emails = [
            "invalid-email",
            "test@",
            "@example.com",
            "test.example.com",
            "test@.com",
            "test@example",
            "",
        ]

        for email in invalid_emails:
            with self.subTest(email=email):
                data = self.valid_data.copy()
                data["username"] = email
                serializer = BaseEmailSerializer(data=data)
                self.assertFalse(serializer.is_valid())
                self.assertIn("username", serializer.errors)
