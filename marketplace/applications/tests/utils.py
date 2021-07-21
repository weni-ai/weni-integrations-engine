from django.contrib.auth import get_user_model

from marketplace.applications.models import AppTypeAsset


User = get_user_model()


def create_app_type_asset(app_code: str, asset_type: str, description: str, created_by: User) -> AppTypeAsset:
    """
    Creates a AppTypeAsset using a test file
    """
    return AppTypeAsset.objects.create(
        app_code=app_code,
        asset_type=asset_type,
        description=description,
        attachment="file_to_upload.txt",
        created_by=created_by,
    )
