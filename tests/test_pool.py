import unittest
import time
import multiprocessing as mp

from pkit.process import Process
from pkit.pool import ProcessPool, Task


class TestTask(unittest.TestCase):
    def test_task_has_default_status(self):
        t = Task(1234)
        self.assertTrue(t.status == Task.READY)

    def test_set_task_status_with_invalid_value_raises(self):
        t = Task(1234)

        with self.assertRaises(ValueError):
            t.status = "ABC 123"


class TestProcessPool(unittest.TestCase):
    def test_execute_acquires_and_releases_slot(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        self.assertEqual(pp.slots.free, 1)

        pp.execute(target=lambda q: q.get(), args=(queue,))
        self.assertEqual(pp.slots.free, 0)
        queue.put('abc')
        time.sleep(0.1)  # Let some time for the on_exit callback execution
        self.assertEqual(pp.slots.free, 1)

    def test_execute_keeps_tasks_store_up_to_date(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        pp.execute(target=lambda q: q.get(), args=(queue,))
        self.assertEqual(len(pp._tasks), 1)
        queue.put('abc')
        time.sleep(0.1)  # Let some time for the on_exit callback execution
        self.assertEqual(len(pp._tasks), 0)

    def test_execute_creates_an_up_to_date_task(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        task = pp.execute(target=lambda q: q.get(), args=(queue,))
        self.assertTrue(isinstance(task, Task))
        self.assertEqual(task.status, Task.RUNNING)

        queue.put('abc')
        time.sleep(0.1)
        self.assertEqual(task.status, Task.FINISHED)

#    def test_close_joins_running_tasks(self):
#        queue = mp.Queue()
#        pp = ProcessPool(1)
#
#        task = pp.execute(target=lambda q: q.get(), args=(queue,))
#        self.assertEqual(pp.slots.free, 0)
#        queue.put('abc')
#        pp.close()
#
#        self.assertEqual(pp.slots.free, 1)

    def test_terminate_kills_running_tasks(self):
        queue = mp.Queue()
        pp = ProcessPool(1)

        task = pp.execute(target=lambda q: q.get(), args=(queue,))
        self.assertEqual(len(pp._tasks), 1)
        self.assertEqual(pp.slots.free, 0)

        pp.terminate(wait=True)
        self.assertEqual(len(pp._tasks), 0)
        self.assertEqual(pp.slots.free, 1)

    def test_on_process_exit_cleanups_the_tasks_store(self):
        pp = ProcessPool(1)
        pp.slots.acquire()
        self.assertEqual(pp.slots.free, 0)

        task = Task(1234)
        process = Process()
        pp._tasks[1234] = {
            'task': task,
            'process': process,
        }

        pp.on_process_exit(1234)
        self.assertEqual(pp.slots.free, 1)
        self.assertFalse(1234 in pp._tasks)
        self.assertEqual(task.status, Task.FINISHED)

