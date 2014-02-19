import pytest

import time
import multiprocessing as mp

from pkit.process import Process
from pkit.pool import ProcessPool, Task


class TestTask:
    def test_task_has_default_status(self):
        t = Task(1234)
        assert t.status == Task.READY

    def test_set_task_status_with_invalid_value_raises(self):
        t = Task(1234)

        with pytest.raises(ValueError):
            t.status = "ABC 123"

    def test_finish_sets_status_to_finished(self):
        t = Task(1234)
        t.finish()

        assert t.status == Task.FINISHED


class TestProcessPool:
    def test_execute_acquires_and_releases_slot(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        assert pp.slots.free == 1

        pp.execute(target=lambda q: q.get(), args=(queue,))
        assert pp.slots.free == 0
        queue.put('abc')
        time.sleep(0.1)  # Let some time for the on_exit callback execution
        assert pp.slots.free == 1

    def test_execute_keeps_tasks_store_up_to_date(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        pp.execute(target=lambda q: q.get(), args=(queue,))
        assert len(pp._tasks) == 1
        queue.put('abc')
        time.sleep(0.1)  # Let some time for the on_exit callback execution
        assert len(pp._tasks) == 0

    def test_execute_creates_an_up_to_date_task(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        task = pp.execute(target=lambda q: q.get(), args=(queue,))
        assert isinstance(task, Task) is True
        assert task.status == Task.RUNNING

        queue.put('abc')
        time.sleep(0.1)
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

        task = Task(1234)
        process = Process()
        pp._tasks[1234] = {
            'task': task,
            'process': process,
        }

        pp.on_process_exit(1234)
        assert pp.slots.free == 1
        assert 1234 not in pp._tasks
        assert task.status == Task.FINISHED

