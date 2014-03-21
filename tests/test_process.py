import pytest

import os
import time
import select
import signal
import psutil

from pkit.process import ProcessOpen, Process, get_current_process


def _collect_process(proc):
    if proc.is_alive is True:
        process_pid = proc.pid

        try:
            proc.terminate(wait=True)
        except OSError:
            return 

        assert proc.is_alive is False

        with pytest.raises(psutil.NoSuchProcess):
            psutil.Process(process_pid).is_running()

        try:
            os.wait()
        except OSError:
            return


class TestGetCurrentProcess:
    def test_get_current_process_in_python_interpreter(self):
        current = get_current_process()

        assert isinstance(current, Process) is True
        assert current.pid == os.getpid()
        assert current._child == None
        assert current._parent == None

    def test_get_current_process_while_process_runs(self):
        current = get_current_process()
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        process_pid = process.pid

        assert hasattr(process, '_current') is True
        assert isinstance(process._current, Process) is True
        assert process._current != current
        assert process._current.pid != current.pid

        _collect_process(process)

    def test_get_current_process_is_reset_to_main_after_terminate(self):
        current = get_current_process()
        process = Process(target=lambda: time.sleep(0.1))


        process.start(wait=True)
        process_pid = process.pid
        process.terminate(wait=True)

        assert hasattr(process, '_current') is True
        assert isinstance(process._current, Process) is True
        assert process._current.pid == current.pid

        _collect_process(process)

    # def test_get_current_process_is_reset_to_main_after_join(self):
    #     current = get_current_process()

    #     process = Process(target=lambda: time.sleep(0.1))
    #     process.start(wait=True)
    #     process_pid = process.pid
    #     process.join()

    #     assert hasattr(process, '_current'))
    #     assert isinstance(process._current, Process))
    #     assert process._current.pid == current.pid)


class TestProcessOpen:
    def test_init_with_wait_activated_actually_waits_for_process_to_be_ready(self):
        process = Process(target=lambda: time.sleep(0.1))

        # default wait timeout lasts one second
        process_open = ProcessOpen(process, wait=True)

        # Kill it immediatly
        os.kill(process_open.pid, signal.SIGTERM)

        # Ensure the ready flag has been awaited
        assert process_open.ready is True


        _collect_process(process)

    def test_init_without_wait_activated_does_not_wait(self):
        process = Process(target=lambda: time.sleep(0.1))

        process_open = ProcessOpen(process)
        os.kill(process_open.pid, signal.SIGTERM)
        assert process_open.ready is False

        _collect_process(process)

    def test_init_with_wait_and_low_provided_wait_timeout(self):
        process = Process(target=lambda: time.sleep(0.1))

        # Set up a really low wait timeout value to check if
        # wait is effectively too short for the ready flag to be
        # transmitted from the child process to the parent
        process_open = ProcessOpen(process, wait=True, wait_timeout=0.000001)
        assert process_open.ready is False

        _collect_process(process)

    def test__send_ready_flag_closes_read_pipe_if_provided(self):
        process = Process(target=lambda: time.sleep(0.1))

        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(process)
        process_open._send_ready_flag(write_pipe, read_pipe)

        with pytest.raises(OSError):
            os.read(read_pipe, 128)

        _collect_process(process)

    def test__send_ready_flag_actually_sends_the_ready_flag(self):
        process = Process(target=lambda: time.sleep(0.1))

        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(process)
        process_open._send_ready_flag(write_pipe)

        read, _, _ = select.select([read_pipe], [], [], 0)
        assert len(read) == 1

        _collect_process(process)

    def test__poll_ready_flag_closes_write_pipe_if_provided(self):
        process = Process(target=lambda: time.sleep(0.1))

        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(process)
        process_open._poll_ready_flag(read_pipe, write_pipe)

        with pytest.raises(OSError):
            os.write(write_pipe, str('abc 123').encode('UTF-8'))

        _collect_process(process)

    def test__poll_ready_flag_actually_recv_the_ready_flag(self):
        process = Process(target=lambda: time.sleep(0.1))

        read_pipe, write_pipe = os.pipe()
        process_open = ProcessOpen(process)

        w = os.fdopen(write_pipe, 'w', 128)
        w.write(ProcessOpen.READY_FLAG)
        w.close()

        flag = process_open._poll_ready_flag(read_pipe)
        assert flag is True

        _collect_process(process)

    def test_non_blocking_poll_does_not_wait_for_process_end(self):
        short_target = lambda: time.sleep(0.1)

        ts_before = time.time()
        process_open = ProcessOpen(Process(target=short_target))
        poll_retcode = process_open.poll()  # flag=os.WNOHANG
        popen_retcode = process_open.returncode
        ts_after = time.time()

        assert (ts_after > ts_before) is True
        assert (ts_after - ts_before) <= 0.1

        # Ensure ProcessOpen didn't exit
        assert poll_retcode is None
        assert popen_retcode is None

    def test_blocking_poll_awaits_on_process_end(self):
        short_target = lambda: time.sleep(0.1)

        ts_before = time.time()
        process_open = ProcessOpen(Process(target=short_target))
        poll_retcode = process_open.poll(0)  # hanging waitpid
        popen_retcode = process_open.returncode
        ts_after = time.time()

        assert (ts_after > ts_before) is True
        assert (ts_after - ts_before) >= 0.1

        # Ensure ProcessOpen has exited
        assert poll_retcode is not None
        assert popen_retcode is not None
        assert poll_retcode == 0
        assert popen_retcode == 0

    def test_wait_with_none_timeout_waits_for_execution_to_end(self):
        short_target = lambda: time.sleep(0.1)

        ts_before = time.time()
        process_open = ProcessOpen(Process(target=short_target))
        wait_retcode = process_open.wait()  # Calls poll with hanging flag
        popen_retcode = process_open.returncode
        ts_after = time.time()

        assert (ts_after > ts_before) is True
        assert (ts_after - ts_before) >= 0.1

        # Ensure the ProcessOpen has exited
        assert wait_retcode is not None
        assert popen_retcode is not None
        assert wait_retcode == 0
        assert popen_retcode == 0

    def test_wait_with_timeout_shorter_than_execution_time_returns_none(self):
        execution_duration = 0.1
        wait_timeout = 0.05
        long_target = lambda: time.sleep(execution_duration)

        ts_before = time.time()
        process_open = ProcessOpen(Process(target=long_target))
        wait_retcode = process_open.wait(timeout=wait_timeout)  # timeout < long_target duration 
        popen_retcode = process_open.returncode
        ts_after = time.time()

        assert (ts_after > ts_before) is True
        assert (ts_after - ts_before) >= wait_timeout
        assert (ts_after - ts_before) <= execution_duration

        # Ensure ProcessOpen has not exited yet
        assert wait_retcode is None
        assert popen_retcode is None

    def test_terminate_exits_with_failure_returncode(self):
        process = Process(target=lambda: time.sleep(0.1))

        # Wait for the fork to be made, and the signal to be binded
        process_open = ProcessOpen(process, wait=True)
        process_pid = process_open.pid

        process_open.terminate()
        pid, status = os.waitpid(process_pid, 0)

        assert pid is not None
        assert pid == process_pid
        assert os.WEXITSTATUS(status) == 1
        assert process_open.returncode == 1

        _collect_process(process)

    def test_terminate_ignores_already_exited_processes(self):
        process_open = ProcessOpen(Process(target=None), wait=True)
        process_open.returncode = 24

        process_open.terminate()
        assert process_open.returncode == 24


class TestProcess:
    def test__current_attribute_is_main_process_when_not_started(self):
        process = Process(target=lambda: time.sleep(0.1))

        assert process._current is not None
        assert process._current.pid == os.getpid()
        assert process._current.name == 'MainProcess {0}'.format(process._current.pid)

        _collect_process(process)

    def test__current_attribute_is_process_when_started(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        assert process._current is not None
        assert process._current == process

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        _collect_process(process)

    def test__current_attribute_is_main_process_when_stopped_with_terminate(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        process.terminate(wait=True)

        assert process.is_alive is False
        with pytest.raises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        assert process._current is not None
        assert process._current.pid == os.getpid()
        assert process._current.name == 'MainProcess {0}'.format(process._current.pid)

        _collect_process(process)

    def test__current_attribute_is_main_process_when_stopped_with_sigterm(self):
        pass  # See todo about sigterm proper support

    def test_is_alive_is_false_when_in_parent_process(self):
        process = Process(target=lambda: time.sleep(0.1))

        assert process.is_alive is False

        _collect_process(process)

    def test_is_alive_is_false_when_child_is_none(self):
        process = Process(target=lambda: time.sleep(0.1))

        process._child = None

        assert process.is_alive is False

        _collect_process(process)

    def test_is_alive_is_false_when_child_has_no_pid(self):
        process = Process(target=lambda: time.sleep(0.1))

        child = ProcessOpen(process)
        child.pid = None
        process._child = child

        assert process.is_alive is False

        _collect_process(process)

    def test_is_alive_is_false_when_process_has_received_sigterm(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        assert process.is_alive is False

        _collect_process(process)

    def test_is_alive_when_process_is_running(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        assert process.is_alive is True
        assert psutil.Process(pid_dump).is_running()

        # Nota: no need to waitpid as Process already
        # handles the child process waitpid system call
        # when SIGCHLD signal is triggered
        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        _collect_process(process)

    def test_run_calls_target(self):
        def dummy_target(data):
            data['abc'] = '123'

        dummy_value = {'abc': None}
        p = Process(target=dummy_target, args=(dummy_value,))
        p.run()

        assert 'abc' in dummy_value
        assert dummy_value, {'abc': '123'}

        _collect_process(p)

    def test_run_ignores_none_target(self):
        p = Process()
        p.run()
        assert p.target == None

        _collect_process(p)

    def test_start_calls_run(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        # assert the process is started and alive, when can be sure
        # it runs the run() method as child process will exit as soon
        # as run() returns.
        assert process.is_alive is True
        assert psutil.Process(pid_dump).is_running()

        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        with pytest.raises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        _collect_process(process)

    def test_start_returns_process_pid(self):
        process = Process(target=lambda: time.sleep(0.1))

        pid = process.start()
        pid_dump = process.pid

        assert pid, pid_dump

        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        with pytest.raises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        _collect_process(process)

    def test_start_raises_if_already_running(self):
        process = Process(target=lambda: time.sleep(0.1))

        process.start()
        pid_dump = process.pid

        assert process.is_alive is True
        assert psutil.Process(pid_dump).is_running()

        with pytest.raises(RuntimeError):
            process.start()

        os.kill(pid_dump, signal.SIGTERM)
        process.wait()

        with pytest.raises(psutil.NoSuchProcess):
            psutil.Process(pid_dump).is_running()

        _collect_process(process)

    def test_join_awaits_on_process_exit(self):
        from multiprocessing import Queue

        queue = Queue()
        process = Process(target=lambda q: q.get(), args=(queue,))
        process.start()
        pid_dump = process.pid

        assert process.is_alive is True
        assert psutil.Process(pid_dump).is_running()

        queue.put('1')
        process.join()

        _collect_process(process)

    def test_join_raises_when_child_does_not_exist(self):
        process = Process()

        with pytest.raises(RuntimeError):
            process.join()

        _collect_process(process)

    def test_terminate_shutsdown_child_process(self):
        from multiprocessing import Queue

        queue = Queue()
        process = Process(target=lambda q: q.get(), args=(queue,))
        process.start()
        pid_dump = process.pid

        assert process.is_alive is True
        assert psutil.Process(pid_dump).is_running()

        process.terminate(wait=True)

        _collect_process(process)

    # def test_terminate_returns_a_failure_exit_code(self):
    #     process = Process(target=lambda: time.sleep(0.1))
    #     process.start()
    #     pid_dump = process.pid

    #     assert process.is_alive)
    #     assert psutil.Process(pid_dump).is_running())

    #     process.terminate(wait=True)

    #     assert hasattr(process, '_exitcode'))
    #     assert process._exitcode >= 1)

    #     assert process.is_alive)
    #     with pytest.raises(psutil.NoSuchProcess):
    #         psutil.Process(pid_dump).is_running()

    def test_terminate_raises_when_child_does_not_exist(self):
        process = Process()

        with pytest.raises(RuntimeError):
            process.terminate()

        _collect_process(process)

    def test_restart_raises_with_invalid_policy(self):
        process = Process(target=lambda: time.sleep(0.1))

        with pytest.raises(ValueError):
            process.restart("that's definetly invalid")

        _collect_process(process)
