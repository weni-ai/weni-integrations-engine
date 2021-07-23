from django.core.exceptions import ValidationError
from marketplace import applications


def validate_app_code_exists(value):
    try:
        applications.types.get_type(value)
    except KeyError:
        raise ValidationError(f"AppType ({value}) not exists!")
