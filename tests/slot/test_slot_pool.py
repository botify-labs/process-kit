import pytest

from pkit.slot.pool import SlotPool


class TestSlotPool:
    def test_acquire(self):
        pool = SlotPool(2)
        assert pool.size == 2
        assert pool.free == 2

        pool.acquire()

        assert pool.size == 2
        assert pool.free == 1

    def test_release(self):
        pool = SlotPool(2)
        assert pool.size == 2
        assert pool.free == 2

        pool.acquire()
        pool.acquire()
        pool.release()

        assert pool.size == 2
        assert pool.free == 1

    def test_release_overflow(self):
        pool = SlotPool(2)
        assert pool.size == 2
        assert pool.free == 2

        with pytest.raises(ValueError):
            pool.release()
