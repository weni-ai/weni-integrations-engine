from unittest import TestCase

from django.conf import settings

from ...types import AppTypesDict, _get_apptypes_members


class FakeType:
    def __init__(self, code, category, name) -> None:
        self.code = code
        self.category = category
        self.name = name


class AppTypesDictTestCase(TestCase):
    def setUp(self):
        self.apptypes = AppTypesDict()
        self.apptypes["wwc"] = FakeType("wwc", "channel", "Weni Web Chat")
        self.apptypes["tg"] = FakeType("tg", "channel", "Telegram")
        self.apptypes["rc"] = FakeType("rc", "chat", "Rocket Chat")

    def test_get_method_returns_right_apptype(self):
        self.assertEqual(self.apptypes.get("wwc").code, "wwc")

    def test_get_method_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.apptypes.get("wrong")

    def test_filter_method_returns_apptype_dict(self):
        def filter_(apptype):
            return apptype.category == "channel"

        self.assertEqual(type(self.apptypes.filter(filter_)), AppTypesDict)

    def test_len_from_filter_method_with_channel_category(self):
        def filter_(apptype):
            return apptype.category == "channel"

        self.assertEqual(len(self.apptypes.filter(filter_)), 2)

    def test_len_from_filter_method_with_chat_category(self):
        def filter_(apptype):
            return apptype.category == "chat"

        self.assertEqual(len(self.apptypes.filter(filter_)), 1)

    def test_len_from_filter_method_with_wrong_category(self):
        def filter_(apptype):
            return apptype.category == "wrong"

        self.assertEqual(len(self.apptypes.filter(filter_)), 0)


class FunctionsTestCase(TestCase):
    def test_get_app_types_members(self):
        members = list(_get_apptypes_members())
        self.assertEqual(len(members), len(settings.APPTYPES_CLASSES))
