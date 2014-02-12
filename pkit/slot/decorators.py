import functools

from pkit.slot import get_slot_pool


def acquire(pool_name):
    """Actor's method decorator to auto-acquire a slot before execution"""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            slots_pool = get_slot_pool(pool_name)

            try:
                slots_pool.acquire()
            except OSError:
                pass

            res = method(self, *args, **kwargs)
            return res
        return wrapper
    return decorator


def release(pool_name):
    """Actors method decorator to auto-release a used slot after execution"""
    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            slots_pool = get_slot_pool(pool_name)
            res = method(self, *args, **kwargs)

            try:
                slots_pool.release()
            except OSError:
                pass

            return res

        return wrapper
    return decorator
