from unittest.mock import patch, MagicMock
from datetime import datetime

from django.test import TestCase

from ..queue import QueueItem, QueueItemManager
from ..exceptions import InvalidItemStatus


class QueueItemTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.fake_body = {
            "uid": "fakeuid",
            "status": QueueItem.STATUS_DEPLOYING,
            "created_at": datetime.now(),
        }

    def test_setup_without_body(self):
        item = QueueItem()
        self.assertTrue(hasattr(item, "uid"))
        self.assertTrue(hasattr(item, "status"))
        self.assertEqual(item.status, QueueItem.STATUS_DEPLOYING)
        self.assertTrue(hasattr(item, "created_at"))

    def test_setup_with_body(self):
        item = QueueItem(self.fake_body)
        self.assertEqual(item.uid, self.fake_body.get("uid"))
        self.assertEqual(item.status, self.fake_body.get("status"))
        self.assertEqual(item.created_at, self.fake_body.get("created_at"))

    def test_update_item_status_with_wrong_data(self):
        item = QueueItem()
        with self.assertRaises(InvalidItemStatus):
            item.update(status="fakestatus")

    def test_update_item_status_with_correct_data(self):
        item = QueueItem(self.fake_body)
        item.update(status=QueueItem.STATUS_DONE)

        self.assertEqual(item.status, QueueItem.STATUS_DONE)

        self.assertEqual(item.uid, self.fake_body.get("uid"))
        self.assertEqual(item.created_at, self.fake_body.get("created_at"))


class QueueItemManagerTestCase(TestCase):
    def setUp(self):
        super().setUp()

        self.items = []

        for item_id in range(5):
            item = QueueItem()
            item.update(uid=f"fake_uid_test-{item_id}")
            self.items.append(item)

    def tearDown(self):
        super().tearDown()

        item_manager = QueueItemManager()

        for item in self.items:
            if item_manager.get(item.uid) is not None:
                item_manager.remove(item)

    def tests_if_adding_an_item_increases_the_queue_size(self):
        item_manager = QueueItemManager()
        current_queue_size = len(item_manager)

        for amount, item in enumerate(self.items):
            item_manager.add(item)
            self.assertEqual(amount + 1 + current_queue_size, len(item_manager))
