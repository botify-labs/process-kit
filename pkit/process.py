import sys
import os
import time
import errno
import signal
import select
import traceback

from multiprocessing.forking import Popen

JOIN_RESTART_POLICY = 0
TERMINATE_RESTART_POLICY = 1


def get_current_process():
    class CurrentProcess(Process):
        def __init__(self, *args, **kwargs):
            self._child = None
            self._parent = None
            self._parent_pid = None
            self.name = 'MainProcess {1}'.format(self.__class__.__name__, os.getpid())
            self.daemonic = False

        @property
        def pid(self):
            return os.getpid()

    return CurrentProcess()


class ProcessOpen(object):
    """ProcessOpen forks the current process and runs a Process object
    create() method in the child process.

    If the child process fork fails, the Process object cleanup routine method
    is called to make sure the object _child attribute is set to None.

    The ProcessOpen objects are not reusable and are only meant to be used as a
    one shot process execution tracker.

    :param  process: Process whom create method should be called in the child process
    :type   process: pkit.process.Process
    """
    READY_FLAG = "READY"

    def __init__(self, process, wait=False, wait_timeout=1):
        sys.stdout.flush()
        sys.stderr.flush()
        self.process = process
        self.returncode = None

        self.ready = None
        read_pipe, write_pipe = os.pipe()

        self.pid = os.fork()
        if self.pid == 0:
            signal.signal(signal.SIGTERM, self.on_sigterm)

            # Once the child process has it's signal handler
            # binded we warn the parent process through a pipe
            if wait is True:
                self._send_ready_flag(write_pipe, read_pipe)

            returncode = self.process.create()
            sys.stdout.flush()
            sys.stderr.flush()
            os._exit(returncode)
        else:
            if wait is True:
                self.ready = self._poll_ready_flag(read_pipe, write_pipe, wait_timeout)

    def _send_ready_flag(self, write_pipe, read_pipe=None):
        """Ran in the forked child process"""
        if read_pipe is not None:
            os.close(read_pipe)

        write_pipe = os.fdopen(write_pipe, 'w', 128)
        write_pipe.write(self.READY_FLAG)
        write_pipe.close()

    def _poll_ready_flag(self, read_pipe, write_pipe=None, timeout=0):
        """Polls the child process read-only pipe for incoming data"""
        if write_pipe is not None:
            os.close(write_pipe)

        try:
            read, _, _ = select.select([read_pipe], [], [], timeout)
        except select.error as e:
            if hasattr(e, 'errno') and e.errno == errno.EINTR:
                return False  # If select is interrupted, we don't care about ready flag
        if len(read) > 0:
            return True

        return False

    def poll(self, flag=os.WNOHANG):
        if self.returncode is None:
            while True:
                try:
                    pid, sts = os.waitpid(self.pid, flag)
                except os.error as e:
                    if e.errno == errno.EINTR:
                        continue
                    # Child process not yet created. See #1731717
                    # e.errno == errno.ECHILD == 10
                    return None
                else:
                    break
            if pid == self.pid:
                if os.WIFSIGNALED(sts):
                    self.returncode = -os.WTERMSIG(sts)
                else:
                    assert os.WIFEXITED(sts)
                    self.returncode = os.WEXITSTATUS(sts)

        return self.returncode

    def wait(self, timeout=None):
        """Polls the forked process for it's status.

        It uses os.waitpid under the hood, and checks for the
        forked process exit code status.

        Poll method source code: http://hg.python.org/cpython/file/ab05e7dd2788/Lib/multiprocessing/forking.py

        :param  timeout: time interval to poll the forked process status
        :type   timeout: float

        :returns: the forked process exit code status
        :rtype: int
        """
        if timeout is None:
            return self.poll(0)

        deadline = time.time() + timeout
        delay = 0.0005

        while 1:
            returncode = self.poll()
            if returncode is not None:
                break

            remaining = deadline - time.time()
            if remaining <= 0:
                break

            delay = min(delay * 2, remaining, 0.05)
            time.sleep(delay)

        self.process.clean()

        return returncode


    # def wait(self, timeout=None):
    #     """Polls the forked process for it's status.

    #     It uses os.waitpid under the hood, and checks for the
    #     forked process exit code status.

    #     Poll method source code: http://hg.python.org/cpython/file/ab05e7dd2788/Lib/multiprocessing/forking.py

    #     :param  timeout: time interval to poll the forked process status
    #     :type   timeout: float

    #     :returns: the forked process exit code status
    #     :rtype: int
    #     """
    #     returncode = super(ProcessOpen, self).wait(timeout)
    #     self.process.clean()

    #     return returncode

    def terminate(self):
        """Kills the running forked process using the SIGTERM signal

        The method checks if the process is actually running, and
        will therefore send it a SIGTERM signal, and wait for it to
        exit before it returns.

        The process object cleanup routine method is then called
        to make sur the object _child attribute is set to None
        """
        if self.returncode is None:
            try:
                os.kill(self.pid, signal.SIGTERM)
            except OSError as e:
                if self.wait(timeout=0.1) is None:
                    raise

            self.returncode = 1

        return self.returncode

    def on_sigterm(self, signum, sigframe):
        """Subprocess sigterm signal handler"""
        self.returncode = 1
        os._exit(1)


class Process(object):
    """Process objects represent activity that is run in a child process

    :param  target: callable object to be invoked in the run method
    :type   target: callable

    :param  name: sets the process name
    :type   name: str

    :param  on_exit: callback to be invoked on process exit,
                     will be provided with current process as first
                     argument. Should be of the form: lambda process: ...
    :type   on_exit: callable

    :param  args: arguments to provide to the target
    :type   args: tuple

    :param  kwargs: keyword arguments to provide to the target
    :type   kwargs: dict
    """
    def __init__(self, target=None, name=None,
                 parent=False, on_exit=None, args=(), kwargs={}):
        self._current = get_current_process()
        self._parent_pid = self._current.pid
        self._child = None
        self._parent = None
        self._exitcode = None
        self._on_exit = on_exit

        self.name = name or self.__class__.__name__
        self.daemonic = False
        self.target = target
        self.target_args = tuple(args)
        self.target_kwargs = dict(kwargs)

        # Bind signals handlers
        signal.signal(signal.SIGCHLD, self.on_sigchld)
        signal.siginterrupt(signal.SIGCHLD, False)

    def __str__(self):
        return '<{0} {1}>'.format(self.name, self.pid)

    def __repr__(self):
        return self.__str__()

    def on_sigchld(self, signum, sigframe):
        if self._child is not None and self._child.pid:
            pid, status = os.waitpid(self._child.pid, os.WNOHANG)
            if pid == self._child.pid:
                self._exitcode = os.WEXITSTATUS(status)

            if self._on_exit:
                self._on_exit(self)

            self.clean()

    def create(self):
        """Method to be called when the process child is forked"""
        # Global try/except designed to catch
        # SystemExit and any uncaught exceptions
        # while run() method execution.
        try:
            try:
                sys.stdin.close()
                sys.stdin = open(os.devnull)
            except (OSError, ValueError):
                pass

            # Run the process target and cleanup
            # the instance afterwards.
            self._current = self
            self.run()
            returncode = 0
        except SystemError as err:
            if not err.args:
                returncode = 1
            elif isinstance(err.args[0], int):
                returncode = err.args[0]
            else:
                sys.stderr.write(str(err.args[0]) + '\n')
                sys.stderr.flush()
                returncode = 0 if isinstance(err.args[0], str) else 1
        except:
            returncode = 1
            sys.stderr.write('Process {} with pid {}:\n'.format(self.name, self.pid))
            sys.stderr.flush()
            traceback.print_exc()

        return returncode

    def clean(self):
        """Cleans up the object child process status"""
        self._current = get_current_process()
        if self._child is not None:
            self._child = None

    def run(self):
        """Runs the target with provided args and kwargs in a fork"""
        if self.target:
            self.target(*self.target_args, **self.target_kwargs)

    def start(self, wait=False, wait_timeout=0):
        """Starts the Process"""
        if os.getpid() != self._parent_pid:
            raise RuntimeError(
                "Can only start a process object created by current process"
            )
        if self._child is not None:
            raise RuntimeError("Cannot start a process twice")

        self._child = ProcessOpen(self, wait=wait, wait_timeout=wait_timeout)
        child_pid = self._child.pid
        self._current = self

        return child_pid

    def join(self, timeout=None):
        """Awaits on Process exit

        :param  timeout: Time to wait for the process exit
        :type   timeout: float
        """
        if self._child is None:
            raise RuntimeError("Can only join a started process")

        try:
            self._exitcode = self._child.wait(timeout)
        except OSError:
            pass

    def terminate(self, wait=False):
        """Forces the process to stop

        The method checks if the process is actually running, and
        will therefore send it a SIGTERM signal, and wait for it to
        exit before it returns.
        """
        if self._child is None:
            raise RuntimeError("Can only terminate a started process")

        self._child.terminate()

        if wait:
            self.wait(until=lambda p, *args: p._child is None)

    def restart(self, policy=JOIN_RESTART_POLICY):
        if not policy in [JOIN_RESTART_POLICY, TERMINATE_RESTART_POLICY]:
            raise ValueError("Invalid restart policy supplied")

        if policy == JOIN_RESTART_POLICY:
            self.join()
        elif policy == TERMINTE_RESTART_POLICY:
            pid_dump = self.pid
            self.terminate()
            os.waitpid(pid_dump, 0)

        self.start()

    def wait(self, until=None, args=(), timeout=None):
        """Wait until the provided predicate about the Process
        object becomes true.

        Default behavior (if until is not provided) is to call
        wait on Process subprocess using the provided timeout.

        The method can be useful in some specific case where you
        would want to wait for specific process states before taking
        any other actions.

        Typically, it could be useful when you'd like to wait
        for a sigterm to be taken in account by the process before
        taking any other actions.

        example:
            p = Process(target=lambda: time.sleep(100))
            p.start()

            os.kill(p.pid, signal.SIGTERM)
            p.wait()

        :param  until: Callable predicate to be evaluated against the
                       process. Takes a process obj and an args tuple
                       as input.
        :type   until: callable

        :param  args: Args to be supplied to the until predicate callable,
                      default value is an empty tuple.
        :type   args: tuple

        :param  timeout: timeout in seconds
        :type   timeout: float
        """
        def default_until(self, *args):
            if self._child is not None:
                try:
                    self._child.wait(timeout)
                except OSError:
                    pass
                return True

        if until is not None and not hasattr(until, '__call__'):
            raise ValueError("Until parameter must be a callable")

        timeout = timeout or 0.1
        until = until or default_until

        while until(self, *args) is False:
            time.sleep(0.1)

        return

    @property
    def is_alive(self):
        if self._child is None or not self._child.pid:
            return False

        self._child.poll()

        return self._child.returncode is None

    @property
    def exitcode(self):
        return self._exitcode

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = None

        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, str):
            raise TypeError(
                "Name property value has to be a basestring subclass instance. "
                "Got {0} instead.".format(type(value))
            )

        self._name = value

    @property
    def pid(self):
        if self._child is None:
            return None
        return self._child.pid
