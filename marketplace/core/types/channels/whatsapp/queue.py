from django.core.cache import cache
from django.utils.crypto import get_random_string

from .apis import InfrastructureDeployAPI, InfrastructureRemoveAPI


class InfrastructureQueueItem(object): # TODO: Change name later

    STATUS_DEPLOYING = "DEPLOYING"
    STATUS_PROPAGATING = "PROPAGATING"
    STATUS_FAILED = "FAILED"
    STATUS_DONE = "DONE"

    STATUS_CHOICES = [STATUS_DEPLOYING, STATUS_PROPAGATING, STATUS_FAILED, STATUS_DONE]

    CACHE_KEY_PREFIX = "whatsapp-queue-item:"
    CACHE_KEY = CACHE_KEY_PREFIX + "{uid}"

    def __init__(self, body: dict = None):
        if body is not None:
            self._uid = body.get("uid")
            self._status = body.get("status")
        else:
            self._setup_item()

    @property
    def key(self):
        return self.CACHE_KEY.format(uid=self._uid)

    @property
    def body(self):
        return dict(uid=self._uid, status=self._status)

    def get_uid(self) -> str:
        return self._uid

    def update_status(self, status):
        if status not in self.STATUS_CHOICES:
            raise Exception(f"The status must be between: {self.STATUS_CHOICES}")

        self._status = status

    def _setup_item(self):
        self._uid = "sandro" + get_random_string(12) # TODO: Validate if url already in use
        self._status = self.STATUS_DEPLOYING

    def __str__(self) -> str:
        return str(self.body)

    def __repr__(self) -> str:
        return str(self)


class InfrastructureItemManager(object): # TODO: Change name later
    @property
    def keys(self) -> list:
        return cache.keys(InfrastructureQueueItem.CACHE_KEY_PREFIX + "*")

    @property
    def all(self) -> list:
        def get_whatsapp_queue_item_by_key(key):
            body = cache.get(key)
            return InfrastructureQueueItem(body)

        return list(map(get_whatsapp_queue_item_by_key, self.keys))

    def _set_or_update(self, item: InfrastructureQueueItem):
        cache.set(item.key, item.body, None)

    def add(self, item: InfrastructureQueueItem):
        self._set_or_update(item)

    def get(self, uid) -> InfrastructureQueueItem:
        key = InfrastructureQueueItem.CACHE_KEY.format(uid=uid)
        body = cache.get(key)

        if body is not None:
            return InfrastructureQueueItem(body)

    def update(self, item: InfrastructureQueueItem):
        self._set_or_update(item)

    def remove(self, item: InfrastructureQueueItem):
        cache.delete(item.key)

    def clear(self):
        for item in self.all:
            self.remove(item)
