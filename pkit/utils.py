import time

from pkit.exceptions import TimeoutError


def wait(until=None, timeout=None, args=(), kwargs={}):
    if not callable(until):
        raise TypeError("until must be callable")

    elapsed = 0.0

    while until(*args, **kwargs) is False:
        time.sleep(0.005)
        elapsed += 0.005
        
        if timeout is not None and elapsed >= timeout:
            raise TimeoutError

    return
