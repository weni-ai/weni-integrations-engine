from .apis import OnPremiseBusinessProfileAPI, OnPremiseAboutAPI, OnPremisePhotoAPI, OnPremiseBusinessProfile


class Profile(object):
    def __init__(self, business_profile: OnPremiseBusinessProfile, about_text: str, photo_url: str):
        self.photo = photo_url
        self.status = about_text
        self.description = business_profile.description


class OnPremiseProfileFacade(object):
    def __init__(self, base_url: str, auth_token: str) -> None:
        self._base_url = base_url
        self._auth_token = auth_token

        self._busines_profile_api = OnPremiseBusinessProfileAPI(base_url, auth_token)
        self._about_api = OnPremiseAboutAPI(base_url, auth_token)
        self._photo_api = OnPremisePhotoAPI(base_url, auth_token)

    def get_profile(self) -> Profile:
        business_profile = self._busines_profile_api.get_business_profile()
        about_text = self._about_api.get_about_text()
        photo_url = self._photo_api.get_photo_url()

        return Profile(business_profile, about_text, photo_url)

    def set_profile(self, status: str = None, description: str = None, photo: str = None) -> None:
        if status is not None:
            self._about_api.set_about_text(status)

        if description is not None:
            self._busines_profile_api.set_profile_description(description)

        if photo is not None:
            self._photo_api.set_photo(photo)
