from datetime import datetime
from string import ascii_lowercase, digits

from django.core.cache import cache
from django.utils.crypto import get_random_string
from django.conf import settings

from .apis import InfrastructureDeployAPI, InfrastructureRemoveAPI
from .exceptions import InvalidItemStatus, ItemAlreadyInQueue


class QueueItem(object):

    STATUS_DEPLOYING = "DEPLOYING"
    STATUS_PROPAGATING = "PROPAGATING"
    STATUS_FAILED = "FAILED"
    STATUS_DONE = "DONE"

    STATUS_CHOICES = [STATUS_DEPLOYING, STATUS_PROPAGATING, STATUS_FAILED, STATUS_DONE]

    CACHE_KEY_PREFIX = "whatsapp-queue-item:"
    CACHE_KEY = CACHE_KEY_PREFIX + "{uid}"

    def __init__(self, body: dict = None):
        if body is not None:
            self.__dict__.update(body)
        else:
            self._setup_item()

    @property
    def key(self):
        return self.CACHE_KEY.format(uid=self.uid)

    @property
    def url(self):
        return f"https://{self.uid}.wa.weni.ai/"

    def update(self, **kwargs):
        status = kwargs.get("status", None)
        if status is not None and status not in self.STATUS_CHOICES:
            raise InvalidItemStatus(f"The status must be between: {self.STATUS_CHOICES}")

        self.__dict__.update(kwargs)

    def get_random_uid(self):
        # TODO: Validade uid
        return "sandro" + get_random_string(12, allowed_chars=ascii_lowercase + digits)

    def _setup_item(self):
        self.uid = self.get_random_uid()
        self.status = self.STATUS_DEPLOYING
        self.created_at = datetime.now()

    def __str__(self) -> str:
        return str(vars(self))

    def __repr__(self) -> str:
        return str(self)


class BaseQueueItemManager(object):
    @property
    def keys(self) -> list:
        return cache.keys(QueueItem.CACHE_KEY_PREFIX + "*")

    def _set_or_update(self, item: QueueItem):
        cache.set(item.key, vars(item), None)

    def _get_item_by_index(self, index: int) -> QueueItem:
        try:
            return self.all()[-1]
        except IndexError:
            return None

    def __len__(self) -> int:
        return len(self.keys)


class QueueItemManagerCRUD(BaseQueueItemManager):
    def add(self, item: QueueItem):
        if self.get(item.uid) is not None:
            raise ItemAlreadyInQueue(f"The item whose `uid` is `{item.uid}` is already in the queue")
        self._set_or_update(item)

    def get(self, uid) -> QueueItem:
        key = QueueItem.CACHE_KEY.format(uid=uid)
        body = cache.get(key)

        if body is not None:
            return QueueItem(body)

    def update(self, item: QueueItem, **kwargs):
        item.update(**kwargs)
        self._set_or_update(item)

    def remove(self, item: QueueItem):
        cache.delete(item.key)


class QueueItemManager(QueueItemManagerCRUD):
    def _get_all_items(self):
        def get_whatsapp_queue_item_by_key(key):
            body = cache.get(key)
            return QueueItem(body)

        return list(map(get_whatsapp_queue_item_by_key, self.keys))

    def _sort_items_by_created_at(self, items):
        items.sort(key=lambda item: item.created_at)

    def all(self) -> list:
        items = self._get_all_items()
        self._sort_items_by_created_at(items)

        return items

    def done_items(self) -> list[QueueItem]:
        return list(filter(lambda item: item.status == QueueItem.STATUS_DONE, self.all()))

    def clear(self):
        for item in self.all():
            self.remove(item)
