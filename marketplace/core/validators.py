from django.core.exceptions import ValidationError


def validate_app_code_exists(value):
    from marketplace.core import types

    try:
        types.APPTYPES.get(value)
    except KeyError:
        if not validate_generic_app_code_exists(value):
            raise ValidationError(f"AppType ({value}) not exists!")


def validate_generic_app_code_exists(code):
    """
        Checks if the code exists within the generic channels coming from rapidpro,
        if it exists, it returns True.
    """
    from marketplace.connect.client import ConnectProjectClient

    client = ConnectProjectClient()
    response = client.detail_channel_type(channel_code=code)
    if response.status_code == 200:
        return True

    return None
