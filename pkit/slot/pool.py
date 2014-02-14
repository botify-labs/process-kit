import multiprocessing


class SlotPool(object):
    """Execution slots pool

    Helps tracking and limiting parrallel executions. Go ahead
    and define a slots pool to limit the number of parrallel
    executions in your program for example.

    :param  size: Size of the pool, aka how many parrallel
    execution slots can be added.
    :type   size: int
    """
    def __init__(self, size, *args, **kwargs):
        self.size = size or multiprocessing.cpu_count()
        self.free = self.size
        self._semaphore = multiprocessing.Semaphore(self.size)

    def acquire(self):
        self._semaphore.acquire()
        self.free -= 1

    def release(self):
        if (self.free + 1) > self.size:
            raise ValueError("No more slots to release from the pool")

        self._semaphore.release()
        self.free += 1

    def reset(self):
        del self._semaphore
        self._semaphore = multiprocessing.BoundedSemaphore(self.size)
        self.free = self.size
