import unittest

import os
import time
import select
import signal
import psutil

from pkit.process import ProcessOpen, Process, get_current_process


class TestGetCurrentProcess(unittest.TestCase):
    def setUp(self):
        self.process = Process(target=lambda: time.sleep(10))

    def tearDown(self):
        if self.process.is_alive is True:
            process_pid = self.process.pid

            self.process.terminate(wait=True)
            self.assertFalse(self.process.is_alive)

            with self.assertRaises(psutil.NoSuchProcess):
                psutil.Process(process_pid).is_running()

    def test_get_current_process_in_python_interpreter(self):
        current = get_current_process()

        self.assertTrue(isinstance(current, Process))
        self.assertEqual(current.pid, os.getpid())
        self.assertEqual(current._child, None)
        self.assertEqual(current._parent, None)

    def test_get_current_process_while_process_runs(self):
        current = get_current_process()

        self.process.start()
        process_pid = self.process.pid

        self.assertTrue(hasattr(self.process, '_current'))
        self.assertTrue(isinstance(self.process._current, Process))
        self.assertTrue(self.process._current != current)
        self.assertTrue(self.process._current.pid != current.pid)

    def test_get_current_process_is_reset_to_main_after_terminate(self):
        current = get_current_process()

        self.process.start(wait=True)
        process_pid = self.process.pid
        self.process.terminate(wait=True)

        self.assertTrue(hasattr(self.process, '_current'))
        self.assertTrue(isinstance(self.process._current, Process))
        self.assertTrue(self.process._current.pid == current.pid)

    # def test_get_current_process_is_reset_to_main_after_join(self):
    #     current = get_current_process()

    #     process = Process(target=lambda: time.sleep(0.1))
    #     self.process.start(wait=True)
    #     process_pid = self.process.pid
    #     self.process.join()

    #     self.assertTrue(hasattr(self.process, '_current'))
    #     self.assertTrue(isinstance(self.process._current, Process))
    #     self.assertTrue(self.process._current.pid == current.pid)


class TestProcessOpen(unittest.TestCase):
    def setUp(self):
        self.process = Process(target=lambda: time.sleep(10))

    def tearDown(self):
        if self.process.is_alive is True:
            process_pid = self.process.pid

            self.process.terminate(wait=True)
            self.assertFalse(self.process.is_alive)

            with self.assertRaises(psutil.NoSuchProcess):
                psutil.Process(process_pid).is_running()

    def test_init_with_wait_activated_actually_waits_for_process_to_be_ready(self):
        # default wait timeout lasts one second
        process_open = ProcessOpen(self.process, wait=True)

        # Kill it immediatly
        os.kill(process_open.pid, signal.SIGTERM)

        # Ensure the ready flag has been awaited
        self.assertTrue(process_open.ready)

    def test_init_without_wait_activated_does_not_wait(self):
        process_open = ProcessOpen(self.process)
        os.kill(process_open.pid, signal.SIGTERM)
        self.assertFalse(process_open.ready)

    def test_init_with_wait_and_low_provided_wait_timeout(self):
        # Set up a really low wait timeout value to check if
        # wait is effectively too short for the ready flag to be
        # transmitted from the child process to the parent
        process_open = ProcessOpen(self.process, wait=True, wait_timeout=0.000001)
        self.assertFalse(process_open.ready)

    def test__send_ready_flag_closes_read_pipe_if_provided(self):
        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(self.process)
        process_open._send_ready_flag(write_pipe, read_pipe)

        with self.assertRaises(OSError):
            os.read(read_pipe, 128)

    def test__send_ready_flag_actually_sends_the_ready_flag(self):
        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(self.process)
        process_open._send_ready_flag(write_pipe)

        read, _, _ = select.select([read_pipe], [], [], 0)
        self.assertEqual(len(read), 1)

    def test__poll_ready_flag_closes_write_pipe_if_provided(self):
        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(self.process)
        process_open._poll_ready_flag(read_pipe, write_pipe)

        with self.assertRaises(OSError):
            os.write(write_pipe, str('abc 123').encode('UTF-8'))

    def test__poll_ready_flag_actually_recv_the_ready_flag(self):
        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(self.process)

        w = os.fdopen(write_pipe, 'w', 128)
        w.write(ProcessOpen.READY_FLAG)
        w.close()

        flag = process_open._poll_ready_flag(read_pipe)
        self.assertTrue(flag)

    def test_wait_actually_waits_for_the_process_to_end(self):
        short_target = lambda: time.sleep(0.1)

        ts_before = time.time()
        process_open = ProcessOpen(Process(target=short_target))
        process_open.wait()
        ts_after = time.time()

        self.assertTrue(ts_after > ts_before)
        self.assertTrue((ts_after - ts_before) >= 0.1)

    def test_terminate_exits_with_failure_returncode(self):
        # Wait for the fork to be made, and the signal to be binded
        process_open = ProcessOpen(self.process, wait=True)
        process_pid = process_open.pid

        process_open.terminate()
        pid, status = os.waitpid(process_pid, 0)

        self.assertTrue(pid is not None)
        self.assertTrue(pid == process_pid)
        self.assertTrue(os.WEXITSTATUS(status) == 1)
        self.assertTrue(process_open.returncode == 1)

    def test_terminate_ignores_already_exited_processes(self):
        process_open = ProcessOpen(Process(target=None), wait=True)
        process_open.returncode = 24

        process_open.terminate()
        self.assertTrue(process_open.returncode == 24)


class TestProcess(unittest.TestCase):
    def setUp(self):
        self.process = Process(target=lambda: time.sleep(100))

    def tearDown(self):
        if self.process.is_alive is True:
            process_pid = self.process

            self.process.terminate(wait=True)
            self.assertFalse(self.process.is_alive)
            with self.assertRaises(psutil.NoSuchProcess):
                psutil.Process(process_pid).is_running()

    def test__current_attribute_is_main_process_when_not_started(self):
        self.assertTrue(self.process._current is not None)
        self.assertTrue(self.process._current.pid == os.getpid())
        self.assertEqual(
            self.process._current.name,
            'MainProcess {0}'.format(self.process._current.pid)
        )

    def test__current_attribute_is_process_when_started(self):
        self.process.start()
        pid_dump = self.process.pid

        self.assertTrue(self.process._current is not None)
        self.assertTrue(self.process._current == self.process)

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

    def test__current_attribute_is_main_process_when_stopped_with_terminate(self):
        self.process.start()
        pid_dump = self.process.pid

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        self.process.terminate(wait=True)

        self.assertFalse(self.process.is_alive)
        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        self.assertTrue(self.process._current is not None)
        self.assertTrue(self.process._current.pid == os.getpid())
        self.assertTrue(
            self.process._current.name,
            'MainProcess {0}'.format(self.process._current.pid)
        )

    def test__current_attribute_is_main_process_when_stopped_with_sigterm(self):
        pass  # See todo about sigterm proper support

    def test_is_alive_is_false_when_in_parent_process(self):
        self.assertFalse(self.process.is_alive)

    def test_is_alive_is_false_when_child_is_none(self):
        self.process._child = None

        self.assertFalse(self.process.is_alive)

    def test_is_alive_is_false_when_child_has_no_pid(self):
        child = ProcessOpen(self.process)
        child.pid = None
        self.process._child = child

        self.assertFalse(self.process.is_alive)

    def test_is_alive_is_false_when_process_has_received_sigterm(self):
        self.process.start()
        pid_dump = self.process.pid

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

        self.assertFalse(self.process.is_alive)

    def test_is_alive_when_process_is_running(self):
        self.process.start()
        pid_dump = self.process.pid

        self.assertTrue(self.process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

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
        self.assertTrue(p.target == None)

    def test_start_calls_run(self):
        self.process.start()
        pid_dump = self.process.pid

        # assert the process is started and alive, when can be sure
        # it runs the run() method as child process will exit as soon
        # as run() returns.
        self.assertTrue(self.process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_start_returns_process_pid(self):
        pid = self.process.start()
        pid_dump = self.process.pid

        self.assertEqual(pid, pid_dump)

        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

        with self.assertRaises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

    def test_start_raises_if_already_running(self):
        self.process.start()
        pid_dump = self.process.pid

        self.assertTrue(self.process.is_alive)
        self.assertTrue(psutil.Process(pid_dump).is_running())

        with self.assertRaises(RuntimeError):
            self.process.start()

        os.kill(pid_dump, signal.SIGTERM)
        self.process.wait()

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

        process.terminate(wait=True)

    # def test_terminate_returns_a_failure_exit_code(self):
    #     process = Process(target=lambda: time.sleep(100))
    #     process.start()
    #     pid_dump = process.pid

    #     self.assertTrue(process.is_alive)
    #     self.assertTrue(psutil.Process(pid_dump).is_running())

    #     process.terminate(wait=True)

    #     self.assertTrue(hasattr(process, '_exitcode'))
    #     self.assertTrue(process._exitcode >= 1)

    #     self.assertFalse(process.is_alive)
    #     with self.assertRaises(psutil.NoSuchProcess):
    #         psutil.Process(pid_dump).is_running()

    def test_terminate_raises_when_child_does_not_exist(self):
        process = Process()

        with self.assertRaises(RuntimeError):
            process.terminate()

    def test_restart_raises_with_invalid_policy(self):
        with self.assertRaises(ValueError):
            self.process.restart("that's definetly invalid")
