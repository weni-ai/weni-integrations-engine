from django.utils.module_loading import import_string
from django.conf import settings

from marketplace.core.types.base import AppType


class AppTypesDict(dict):
    def get(self, code: str) -> AppType:
        apptype = super().get(code, None)
        return apptype

    def filter(self, function) -> dict:
        filtered = self.__class__()
        for key, value in self.items():
            if function(value):
                filtered[key] = value
        return filtered

APPTYPES = AppTypesDict()


def _get_apptypes_members():
    if settings.APPTYPES_CLASSES is []:
        yield

    for module_path in settings.APPTYPES_CLASSES:
        yield import_string(f"marketplace.core.types.{module_path}")


for member in _get_apptypes_members():
    APPTYPES[member.code] = member()
