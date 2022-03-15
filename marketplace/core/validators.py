from django.core.exceptions import ValidationError


def validate_app_code_exists(value):
    from marketplace.core import types

    try:
        types.APPTYPES.get(value)
    except KeyError:
        raise ValidationError(f"AppType ({value}) not exists!")
