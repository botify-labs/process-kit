import unittest

import os
import time
import signal
import psutil

from pkit.process import ProcessOpen, Process


class TestProcess(unittest.TestCase):
    def test_is_alive_is_false_when_in_parent_process(self):
        process = Process()
        self.assertFalse(process.is_alive)

    def test_is_alive_is_false_when_child_is_none(self):
        process = Process()
        process._child = None

        self.assertFalse(process.is_alive)

    def test_is_alive_is_false_when_child_has_no_pid(self):
        process = Process()
        child = ProcessOpen(process)
        child.pid = None
        process._child = child

        self.assertFalse(process.is_alive)

    def test_is_alive_when_process_is_running(self):
        def dummy_target():
            while True:
                time.sleep(1)

        process = Process(target=dummy_target)
        process.start()
        pid_dump = process.pid

        self.assertTrue(process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        os.kill(pid_dump, signal.SIGTERM)
        os.waitpid(pid_dump, 0)

        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_run_calls_target(self):
        def dummy_target(data):
            data['abc'] = '123'

        dummy_value = {'abc': None}
        p = Process(target=dummy_target, args=(dummy_value,))
        p.run()

        self.assertTrue('abc' in dummy_value)
        self.assertEqual(dummy_value, {'abc': '123'})

    def test_run_ignores_none_target(self):
        p = Process()
        p.run()
        self.assertIsNone(p.target)

    def test_start_calls_run(self):
        process = Process(target=lambda: time.sleep(100))
        process.start()
        pid_dump = process.pid

        # assert the process is started and alive, when can be sure
        # it runs the run() method as child process will exit as soon
        # as run() returns.
        self.assertTrue(process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        os.kill(pid_dump, signal.SIGTERM)
        os.waitpid(pid_dump, 0)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_start_raises_if_already_running(self):
        process = Process(target=lambda: time.sleep(100))
        process.start()
        pid_dump = process.pid

        self.assertTrue(process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        with self.assertRaises(RuntimeError):
            process.start()

        os.kill(pid_dump, signal.SIGTERM)
        os.waitpid(pid_dump, 0)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_join_awaits_on_process_exit(self):
        from multiprocessing import Queue

        queue = Queue()
        process = Process(target=lambda q: q.get(), args=(queue,))
        process.start()
        pid_dump = process.pid

        self.assertTrue(process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        queue.put('1')
        process.join()

        self.assertFalse(process.is_alive)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_join_raises_when_child_does_not_exist(self):
        process = Process()
        with self.assertRaises(RuntimeError):
            process.join()

    def test_terminate_shutsdown_child_process(self):
        from multiprocessing import Queue

        queue = Queue()
        process = Process(target=lambda q: q.get(), args=(queue,))
        process.start()
        pid_dump = process.pid

        self.assertTrue(process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        process.terminate()
        os.waitpid(pid_dump, 0)

        self.assertFalse(process.is_alive)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_terminate_raises_when_child_does_not_exist(self):
        process = Process()
        with self.assertRaises(RuntimeError):
            process.terminate()

    def test_restart_raises_with_invalid_policy(self):
        process = Process(target=lambda: time.sleep(100))

        with self.assertRaises(ValueError):
            process.restart(policy="that's definetly invalid")
