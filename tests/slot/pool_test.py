import unittest

from pkit.slot.pool import SlotPool


class SlotPoolTest(unittest.TestCase):
    def setUp(self):
        self.pool = SlotPool(2)

    def tearDown(self):
        self.pool.reset()

    def test_acquire(self):
        self.assertEqual(self.pool.size, 2)
        self.assertEqual(self.pool.free, 2)

        self.pool.acquire()

        self.assertEqual(self.pool.size, 2)
        self.assertEqual(self.pool.free, 1)

    def test_release(self):
        self.assertEqual(self.pool.size, 2)
        self.assertEqual(self.pool.free, 2)

        self.pool.acquire()
        self.pool.acquire()
        self.pool.release()

        self.assertEqual(self.pool.size, 2)
        self.assertEqual(self.pool.free, 1)

    def test_release_overflow(self):
        self.assertEqual(self.pool.size, 2)
        self.assertEqual(self.pool.free, 2)

        with self.assertRaises(ValueError):
            self.pool.release()
