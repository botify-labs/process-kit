import pytest

from pkit.slot.core import get_slot_pool
import pkit.slot as slot


class TestSlotPoolDecoratorsTest:
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
        assert testpool.free == 3
        obj.test()
        assert testpool.free == 2

    def test_slot_release(self):
        # declare a slot pool with 3 slots
        testpool = get_slot_pool('othertestpool', 3)

        # define a class method using the slot_acquire
        # decorator
        class Dummy(object):
            @slot.release('othertestpool')
            def test(self):
                pass

        assert testpool.free == 3
        obj = Dummy()
        testpool.acquire()
        testpool.acquire()
        obj.test()
        assert testpool.free == 2
