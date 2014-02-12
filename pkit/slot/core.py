import multiprocessing

from pkit.slot.pool import SlotPool


# Module globals. Slots pool is the host dictionary for
# every slots pools create via GetSlotPool calls.
_default_slot_pool_size = multiprocessing.cpu_count()
_slot_pools = {}


def get_slot_pool(name, pool_size=_default_slot_pool_size):
    """Retrieves or create a slot pool from the module global
    slots pool.

    As a default, if slots_pool size is not provided, the host
    cpu count will be used

    :params     name: Name of the slots pool to retrieve/create
    :type       name: string

    :params     pool_size: size (in slots) of the slots pool
    :type       pool_size: int

    :returns: Retrieved or created slot pool
    :rtype: botify.saas.backend.process.slot.pool.SlotPool
    """
    if name not in _slot_pools:
        _slot_pools[name] = SlotPool(pool_size)

    return _slot_pools[name]
