import time

from pkit.exceptions import TimeoutError


DEFAULT_INTERVAL = 0.005


def wait(until=None, timeout=None, args=(), kwargs={}):
    if not callable(until):
        raise TypeError("until must be callable")

    elapsed = 0.0

    interval = DEFAULT_INTERVAL
    while until(*args, **kwargs) is False:
        time.sleep(interval)
        elapsed += interval

        if timeout is not None and elapsed >= timeout:
            raise TimeoutError

    return
