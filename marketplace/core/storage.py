from storages.backends.s3boto3 import S3Boto3Storage


class AppStorage(S3Boto3Storage):  # pragma: no cover
    def __init__(self, app, **settings):
        self._app = app
        super().__init__(**settings)

    def get_default_settings(self):
        default_settings = super().get_default_settings()
        default_settings["location"] = f"apptypes/{self._app.app_code}/{self._app.uuid}/"
        return default_settings
