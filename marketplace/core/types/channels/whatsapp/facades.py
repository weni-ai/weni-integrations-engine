from .apis import OnPremiseBusinessProfileAPI, OnPremiseAboutAPI, OnPremisePhotoAPI


class OnPremiseProfileFacade(object):
    def __init__(self, base_url: str, auth_token: str) -> None:
        self._base_url = base_url
        self._auth_token = auth_token

        self._business_profile_api = OnPremiseBusinessProfileAPI(base_url, auth_token)
        self._about_api = OnPremiseAboutAPI(base_url, auth_token)
        self._photo_api = OnPremisePhotoAPI(base_url, auth_token)

    def get_profile(self) -> dict:
        business_profile = self._business_profile_api.get_profile()
        about_text = self._about_api.get_about_text()
        photo_url = self._photo_api.get_photo_url()

        return dict(
            photo_url=photo_url,
            status=about_text,
            business=dict(
                description=business_profile.description,
                vertical=business_profile.vertical,
            ),
        )

    def set_profile(
        self, photo: str = None, status: str = None, business: dict = None
    ) -> None:
        if photo is not None:
            self._photo_api.set_photo(photo)

        if status is not None:
            self._about_api.set_about_text(status)

        if business is not None:
            self._business_profile_api.set_profile(business)

    def delete_profile_photo(self) -> None:
        self._photo_api.delete_photo()
