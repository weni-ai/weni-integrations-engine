from .requests import CloudProfileRequest


class CloudProfileFacade(object):  # TODO: Interface

    VERTICAl_MAP = {
        "Automotive": "AUTOMOTIVE",
        "Beauty, Spa and Salon": "BEAUTY",
        "Clothing and Apparel": "APPAREL",
        "Education": "ENTERTAIN",
        "Entertainment": "",
        "Event Planning and Service": "",
        "Finance and Banking": "",
        "Food and Grocery": "",
        "Public Service": "",
        "Hotel and Lodging": "",
        "Medical and Health": "",
        "Non-profit": "NONPROFIT",
        "Professional Services": "",
        "Shopping and Retail": "",
        "Travel and Transportation": "",
        "Restaurant": "RESTAURANT",
        "Other": "OTHER",
    }

    def __init__(self, phone_number_id: "str") -> None:
        self._profile_api = CloudProfileRequest(phone_number_id)

    def get_profile(self):
        profile = self._profile_api.get_profile()
        vertical = profile["business"]["vertical"]

        if vertical is not None:
            for key, value in self.VERTICAl_MAP.items():
                if value == vertical:
                    profile["business"]["vertical"] = key

        return profile

    def set_profile(self, photo: str = None, status: str = None, business: dict = {}):
        data = dict()

        if status is not None:
            data["about"] = status

        for key, value in business.items():
            if key == "vertical":
                data[key] = self.VERTICAl_MAP.get(value)
            else:
                data[key] = value

        self._profile_api.set_profile(**data)

    def delete_profile_photo(self):
        pass


class CloudProfileContactFacade(object):  # TODO: Interface
    def __init__(self, phone_number_id: "str") -> None:
        self._profile_api = CloudProfileRequest(phone_number_id)

    def get_profile(self):
        return self._profile_api.get_profile()

    def set_profile(self, data: dict):
        self._profile_api.set_profile(**data)
