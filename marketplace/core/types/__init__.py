import os
import inspect
import importlib

from django.utils.module_loading import import_string
from django.conf import settings

from marketplace.core.types.base import AppType


types_ = []


def _get_app_types_members():
    if settings.APPTYPES_CLASSES is []:
        yield

    for module_path in settings.APPTYPES_CLASSES:
        yield import_string(f"marketplace.core.types.{module_path}")


def get_types(category: str = None) -> list:
    """
    Returns a list of AppTypes

        Parameters:
            category (str): Filter AppTypes by category

        Returns:
            list: A list of AppTypes
    """
    global types_

    app_types = types_.copy()

    if settings.DYNAMIC_APPTYPES:
        app_types += settings.DYNAMIC_APPTYPES

    if category:
        return list(filter(lambda type_: type_.get_category_display() == category, app_types))

    return app_types


def get_type(code: str) -> AppType:
    types = list(filter(lambda type: type.code == code, get_types()))

    if not len(types):
        raise KeyError(f"Invalid code: {code} No AppType found")

    return types[0]


for member in _get_app_types_members():
    types_.append(member())
