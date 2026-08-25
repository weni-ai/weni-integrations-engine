from django.test import SimpleTestCase

from marketplace.core.pacing.tasks import task_drain_paced_queue as pacing_task
from marketplace.core.tasks import task_drain_paced_queue


class CoreTasksDiscoveryTestCase(SimpleTestCase):
    def test_reexports_drain_paced_queue_task(self):
        self.assertIs(task_drain_paced_queue, pacing_task)
