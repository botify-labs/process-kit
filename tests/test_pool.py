import pytest

import multiprocessing as mp

from pkit.process import Process
from pkit.pool import ProcessPool, Task
from pkit.utils import wait
import pkit.signals


def setup_module():
    pkit.signals.base.reset()


def teardown_module():
    pkit.signals.base.reset()


class PoolTestCase:
    def setup_method(self):
        pkit.signals.base.reset()

    def teardown_method(self):
        pkit.signals.base.reset()


class TestTask(PoolTestCase):
    def test_task_has_default_status(self):
        t = Task(1234)
        assert t.status == Task.READY

    def test_set_task_status_with_invalid_value_raises(self):
        t = Task(1234)

        with pytest.raises(ValueError):
            t.status = "ABC 123"

    def test_finish_sets_status_to_finished(self):
        t = Task(Process())
        t.finish()

        assert t.status == Task.FINISHED


class TestProcessPool(PoolTestCase):
    def test_execute_acquires_and_releases_slot(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        assert pp.slots.free == 1

        pp.execute(target=queue.get)
        assert pp.slots.free == 0
        queue.put('')

        # If it timeouts, it means that pp.slots.release() was not called when
        # the child process exited.
        print('waiting...')
        wait(until=lambda: pp.slots.free == 1,
             timeout=0.5)

        assert pp.slots.free == 1

    def test_execute_keeps_tasks_store_up_to_date(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        pp.execute(target=lambda q: q.get(), args=(queue,))
        assert len(pp._tasks) == 1
        queue.put('abc')

        wait(until=lambda pp: len(pp._tasks) == 0, args=(pp,), timeout=0.5)

        assert len(pp._tasks) == 0

    def test_execute_creates_an_up_to_date_task(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        task = pp.execute(target=lambda q: q.get(), args=(queue,))
        assert isinstance(task, Task) is True
        assert task.status == Task.RUNNING

        queue.put('abc')

        wait(until=lambda t: t.status == Task.FINISHED, args=(task,), timeout=0.5)

        assert task.status == Task.FINISHED

# Will be reactivated once the process.join will be fixed
#    def test_close_joins_running_tasks(self):
#        queue = mp.Queue()
#        pp = ProcessPool(1)
#
#        task = pp.execute(target=lambda q: q.get(), args=(queue,))
#        assert pp.slots.free, 0)
#        queue.put('abc')
#        pp.close()
#
#        assert pp.slots.free, 1)

    def test_terminate_kills_running_tasks(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        task = pp.execute(target=lambda q: q.get(), args=(queue,))
        assert len(pp._tasks) == 1
        assert pp.slots.free == 0

        pp.terminate(wait=True)
        assert len(pp._tasks) == 0
        assert pp.slots.free == 1

    def test_on_process_exit_cleanups_the_tasks_store(self):
        pp = ProcessPool(1)
        pp.slots.acquire()
        assert pp.slots.free == 0

        process = Process()
        process._child = lambda: None
        process._child.pid = 1234
        task = Task(process)
        pp._tasks[1234] = task

        pp.on_process_exit(process)
        assert pp.slots.free == 1
        assert 1234 not in pp._tasks
        assert task.status == Task.FINISHED
