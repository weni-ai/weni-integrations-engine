import os
import inspect
import importlib

from marketplace.core.types.base import AppType


_types = []

_types_path = os.path.dirname(__file__)


def _get_modules():
    for content_file in os.listdir(_types_path):
        if content_file.endswith(".py") or content_file == "__pycache__":
            continue

        try:
            module = importlib.import_module(f"marketplace.core.types.{content_file}")
        except ModuleNotFoundError:
            continue

        yield module


def _get_app_types_members() -> list:
    for module in _get_modules():
        for name, member in inspect.getmembers(module):
            if inspect.isclass(member) and issubclass(member, AppType):
                yield member


def get_types(category: str = None) -> list:
    """
    Returns a list of AppTypes

        Parameters:
            category (str): Filter AppTypes by category

        Returns:
            list: A list of AppTypes
    """
    if category:
        return list(filter(lambda _type: _type.get_category_display() == category, _types))

    return _types


def get_type(code: str) -> AppType:
    types = list(filter(lambda type: type.code == code, _types))

    if not len(types):
        raise KeyError(f"Invalid code: {code} No AppType found")

    return types[0]


for member in _get_app_types_members():
    _types.append(member())
