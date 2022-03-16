from .queue import QueueItem, QueueItemManager
from .apis import OnPremiseDeployAPI, OnPremiseRemoveAPI


class OnPromisseQueueFacade(object):
    def __init__(self):
        self.items = QueueItemManager()
        self._deploy_api = OnPremiseDeployAPI()
        self._remove_api = OnPremiseRemoveAPI()

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
