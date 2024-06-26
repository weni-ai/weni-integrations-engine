from marketplace.clients.facebook.client import FacebookClient
from marketplace.services.facebook.service import PhotoAPIService, CloudProfileService
from marketplace.interfaces.facebook.interfaces import CloudProfileRequestsInterface


class CloudProfileFacade(CloudProfileRequestsInterface):
    # TODO: Put vertical rule in respective serializer

    VERTICAl_MAP = {
        "Automotive": "AUTO",
        "Beauty, Spa and Salon": "BEAUTY",
        "Clothing and Apparel": "APPAREL",
        "Education": "EDU",
        "Entertainment": "ENTERTAIN",
        "Event Planning and Service": "EVENT_PLAN",
        "Finance and Banking": "FINANCE",
        "Food and Grocery": "GROCERY",
        "Public Service": "GOVT",
        "Hotel and Lodging": "HOTEL",
        "Medical and Health": "HEALTH",
        "Non-profit": "NONPROFIT",
        "Professional Services": "PROF_SERVICES",
        "Shopping and Retail": "RETAIL",
        "Travel and Transportation": "TRAVEL",
        "Restaurant": "RESTAURANT",
        "Other": "OTHER",
    }

    def __init__(self, access_token: str, phone_number_id: "str") -> None:
        self.facebook_client = FacebookClient(access_token)
        self._profile_api = CloudProfileService(
            client=self.facebook_client.get_profile_requests(phone_number_id)
        )
        self._photo_api = PhotoAPIService(client=self.facebook_client)
        self._phone_number_id = phone_number_id

    def get_profile(self):
        profile = self._profile_api.get_profile()
        vertical = profile["business"]["vertical"]

        if vertical is not None:
            for key, value in self.VERTICAl_MAP.items():
                if value == vertical:
                    profile["business"]["vertical"] = key

        return profile

    def set_profile(self, photo: str = None, status: str = None, business: dict = {}):
        if photo is not None:
            self._photo_api.set_photo(photo, self._phone_number_id)

        data = dict()

        if status is not None:
            data["about"] = status

        for key, value in business.items():
            if key == "vertical":
                data[key] = self.VERTICAl_MAP.get(value)
            else:
                data[key] = value

        self._profile_api.set_profile(**data)

    def delete_profile_photo(self) -> None:
        return self._profile_api.delete_profile_photo()


class CloudProfileContactFacade(CloudProfileRequestsInterface):
    def __init__(self, access_token: str, phone_number_id: "str") -> None:
        self.facebook_client = FacebookClient(access_token)
        self._profile_api = CloudProfileService(
            client=self.facebook_client.get_profile_requests(phone_number_id)
        )

    def get_profile(self):
        return self._profile_api.get_profile()

    def set_profile(self, data: dict):
        self._profile_api.set_profile(**data)

    def delete_profile_photo(self) -> None:
        return self._profile_api.delete_profile_photo()
