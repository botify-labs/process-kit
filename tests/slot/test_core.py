import pytest
import multiprocessing

from pkit.slot.pool import SlotPool
from pkit.slot.core import get_slot_pool


class TestGetSlotPool:
    def test_get_slot_pool(self):
        p = get_slot_pool('test')

        assert isinstance(p, SlotPool)
        assert p.size == multiprocessing.cpu_count()

    def test_get_slot_pool_with_already_existing_slot(self):
        first = get_slot_pool('first', 2)
        first.acquire()

        second = get_slot_pool('first')

        assert isinstance(first, SlotPool)
        assert isinstance(second, SlotPool)
        assert second.size == 2
        assert second.free == 1
