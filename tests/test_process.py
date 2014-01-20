import unittest

import os
import time
import signal
import psutil

from mock import patch

from pkit.process import ProcessOpen, Process, get_current_process


class TestGetCurrentProcess(unittest.TestCase):
    def test_get_current_process_in_python_interpreter(self):
        current = get_current_process()

        self.assertTrue(isinstance(current, Process))
        self.assertEqual(current.pid, os.getpid())
        self.assertEqual(current._child, None)
        self.assertEqual(current._parent, None)

    def test_get_current_process_inside_a_subprocess(self):
        from multiprocessing import Manager
        def get_child_current(d):
            d['get_current_process().pid'] = get_current_process().pid

        manager = Manager()
        current_pid = os.getpid()
        subprocess_infos = manager.dict({'get_current_process().pid': None})

        process = Process(target=get_child_current, args=(subprocess_infos,))
        process.start()
        process.join()

        self.assertTrue(process._current.pid == current_pid)
        self.assertTrue('get_current_process().pid' in subprocess_infos)
        self.assertTrue(isinstance(subprocess_infos['get_current_process().pid'], int))
        self.assertTrue(subprocess_infos['get_current_process().pid'] != current_pid)


class TestProcessOpen(unittest.TestCase):
    def test_init_with_raising_fork(self):
        process = Process(target=lambda: time.sleep(100))
        process._child = 'abc 123'  # We just want to check the value will be None

        with patch('os.fork', side_effect=OSError()):
            with self.assertRaises(OSError):
                ProcessOpen(process)

        self.assertIsNone(process._child)


class TestProcess(unittest.TestCase):
    def test__current_attribute_is_main_process_when_not_started(self):
        process = Process()

        self.assertTrue(process._current is not None)
        self.assertTrue(process._current.pid == os.getpid())
        self.assertEqual(
            process._current.name,
            'MainProcess {0}'.format(process._current.pid)
        )

    def test__current_attribute_is_process_when_started(self):
        process = Process(target=lambda: time.sleep(100))
        process.start()
        pid_dump = process.pid

        self.assertTrue(process._current is not None)
        self.assertTrue(process._current == process)

        os.kill(pid_dump, signal.SIGTERM)
        os.waitpid(pid_dump, 0)

        self.assertFalse(process.is_alive)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test__current_attribute_is_main_process_when_stopped_with_terminate(self):
        process = Process(target=lambda: time.sleep(100))
        process.start()
        pid_dump = process.pid

        process.terminate()
        os.waitpid(pid_dump, 0)

        self.assertFalse(process.is_alive)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        self.assertTrue(process._current is not None)
        self.assertTrue(process._current.pid == os.getpid())
        self.assertTrue(
            process._current.name,
            'MainProcess {0}'.format(process._current.pid)
        )

    def test__current_attribute_is_main_process_when_stopped_with_sigterm(self):
        pass  # See todo about sigterm proper support

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

    def test_is_alive_is_false_when_process_has_received_sigterm(self):
        process = Process()
        process.start()
        pid_dump = process.pid

        os.kill(pid_dump, signal.SIGTERM)
        os.waitpid(pid_dump, 0)

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
