import unittest

from pkit.slot.core import get_slot_pool
import pkit.slot as slot


class SlotPoolDecoratorsTest(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_slot_acquire(self):
        # declare a slot pool with 3 slots
        testpool = get_slot_pool('testpool', 3)

        # define a class method using the slot_acquire
        # decorator
        class Dummy(object):
            @slot.acquire('testpool')
            def test(self):
                pass

        obj = Dummy()
        self.assertEqual(testpool.free, 3)
        obj.test()
        self.assertEqual(testpool.free, 2)

    def test_slot_release(self):
        # declare a slot pool with 3 slots
        testpool = get_slot_pool('othertestpool', 3)

        # define a class method using the slot_acquire
        # decorator
        class Dummy(object):
            @slot.release('othertestpool')
            def test(self):
                pass

        self.assertEqual(testpool.free, 3)
        obj = Dummy()
        testpool.acquire()
        testpool.acquire()
        obj.test()
        self.assertEqual(testpool.free, 2)
