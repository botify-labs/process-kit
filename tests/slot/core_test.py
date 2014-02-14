import unittest
import multiprocessing

from botify.saas.backend.process.slot.pool import SlotPool
from botify.saas.backend.process.slot.core import get_slot_pool


class GetSlotPoolTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_slot_pool(self):
        p = get_slot_pool('test')

        self.assertIsInstance(p, SlotPool)
        self.assertEqual(p.size, multiprocessing.cpu_count())

    def test_get_slot_pool_with_already_existing_slot(self):
        first = get_slot_pool('first', 2)
        first.acquire()

        second = get_slot_pool('first')

        self.assertIsInstance(first, SlotPool)
        self.assertIsInstance(second, SlotPool)
        self.assertEqual(second.size, 2)
        self.assertEqual(second.free, 1)
