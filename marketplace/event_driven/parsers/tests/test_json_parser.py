from unittest import TestCase

from ..json_parser import JSONParser
from ..exceptions import ParseError


class JSONParserTestCase(TestCase):
    def test_parse_invalid_stream_format(self):
        stream = b"abcd"

        with self.assertRaises(ParseError):
            JSONParser().parse(stream)

    def test_parse_empty_stream(self):
        stream = b""

        with self.assertRaises(ParseError):
            JSONParser().parse(stream)

    def test_parse_invalid_encoding(self):
        stream = b'{\r\n    "code": "123"\r\n}'

        with self.assertRaises(LookupError):
            JSONParser().parse(stream, encoding="123")

    def test_parse_valid_json_and_encoding(self):
        stream = b'{\r\n    "code": "123"\r\n}'
        json_parsed = JSONParser().parse(stream)

        self.assertEqual(json_parsed, {"code": "123"})
