from django.utils.crypto import get_random_string

from .queue import QueueItem, QueueItemManager
from .apis import OnPremiseDeployManifestAPI, OnPremiseRemoveManifestAPI, OnPremisePasswordAPI


class OnPremiseQueueFacade(object):
    def __init__(self):
        self.items = QueueItemManager()
        self._deploy_api = OnPremiseDeployManifestAPI()
        self._remove_api = OnPremiseRemoveManifestAPI()

    def deploy_whatsapp(self, item: QueueItem):
        self.items.add(item)
        self._deploy_api.deploy(item)

    def remove_whatsapp(self, item: QueueItem):
        self._remove_api.remove(item)
        self.items.remove(item)  # TODO: Remove only after confirmation

    def book_whatsapp(self) -> str:
        item = self.items.done_items()[-1]
        self.items.remove(item)
        return item.url


class OnPremiseFacade(object):
    def __init__(self) -> None:
        self._password_api = OnPremisePasswordAPI()

    def _get_new_password(self) -> str:
        chars = "wFEdGu9ckN!JVKpSrA8WRHnDzsPU3Ca45q7h2tQbeY_xvjg+f@MyBZTX?-m6"
        return get_random_string(20, chars)

    def change_password(self, onpremise_url: str) -> str:
        new_password = self._get_new_password()
        self._password_api.change(onpremise_url, new_password)

        return new_password
