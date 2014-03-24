import uuid

from pkit.process import Process
from pkit.slot import SlotPool


class Task(object):
    """Tracks a ProcessPool execution

    :param  process_pid: process execution pid to track
    :type   process_pid: int

    :param  _id: specify explictly the task id, if not provided
                 a random one will be generated.
    :type   _id: string

    :param  status: task execution status
    :type   status: member of Task.STATUSES
    """
    READY = 'ready'
    RUNNING = 'running'
    FINISHED = 'finished'

    STATUSES = (
        READY,
        RUNNING,
        FINISHED
    )

    def __init__(self, process, _id=None, status=None):
        self.id = _id or uuid.uuid4().hex
        self.exitcode = None
        self.process = process

        if status:
            self.status = status

    def __str__(self):
        return '<Task {} {}>'.format(self.id, self.status)

    def finish(self):
        self._status = Task.FINISHED

    @property
    def status(self):
        if not hasattr(self, '_status'):
            self._status = Task.READY

        return self._status

    @status.setter
    def status(self, value):
        if not value in Task.STATUSES:
            raise ValueError("Invalid status provided")
        self._status = value

    @property
    def running(self):
        return self.status == Task.RUNNING

    @property
    def finished(self):
        return self.status == Task.FINISHED


class ProcessPool(object):
    """Bounded parrallel execution pool through processes

    ProcessPool differs from commonly used execution pools
    as it will block as soon as there are no available slots
    for supplied execution request.

    :param  slots: how many parrallel executions can be
                   done at the same time.
    :type   slots: int
    """
    def __init__(self, slots=None):
        # If slots is None, the slots pool will
        # automatically set it's size to the host
        # cpu count.
        self.slots = SlotPool(slots)
        self.processes = {}
        self._tasks = {}

        self.ready = True

    def execute(self, target, args=(), kwargs={}):
        """Adds a task execution to the pool

        Will block until a slot is available if none is available
        at the moment.

        :param  target: callable object to be invoked in the run method
        :type   target: callable

        :param  args: arguments to provide to the target
        :type   args: tuple

        :param  kwargs: keyword arguments to provide to the target
        :type   kwargs: dict
        """
        if not self.ready is True:
            return

        # Unix semaphores are acquired through sem_post and sem_wait
        # syscalls, which can potentially fail. an OSError is then raised.
        self.slots.acquire()
        process = Process(
            target=target,
            args=args,
            kwargs=kwargs,
            on_exit=self.on_process_exit,
        )

        process_pid = process.start(wait=True)
        task = Task(process, status=Task.RUNNING)

        self._tasks[process_pid] = task

        return task

    def close(self, timeout=None):
        self.ready = False

        for task in list(self._task.values()):
            task.process.join(timeout=timeout)

    def terminate(self, wait=False):
        self.ready = False

        for task in list(self._tasks.values()):
            task.process.terminate(wait=wait)

    def on_process_exit(self, process):
        self.slots.release()

        pid = process.pid
        if pid in self._tasks:
            self._tasks[pid].status = Task.FINISHED
            self._tasks[pid].exitcode = self._tasks[pid].process.exitcode
            del self._tasks[pid]
