import sys
import os
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


class ProcessOpen(Popen):
    """ProcessOpen forks the current process and runs a Process object
    create() method in the child process.

    If the child process fork fails, the Process object cleanup routine method
    is called to make sure the object _child attribute is set to None.

    :param  process: Process whom create method should be called in the child process
    :type   process: pkit.process.Process
    """
    def __init__(self, process):
        sys.stdout.flush()
        sys.stderr.flush()
        self.process = process
        self.returncode = None

        try:
            self.pid = os.fork()
            if self.pid == 0:
                exit_code = self.process.create()
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(exit_code)
        except OSError:
            self.process.clean()
            raise

    def wait(self, timeout=None):
        """Polls the forked process for it's status.

        It uses os.waitpid under the hood, and checks for the
        forked process exit code status.

        The process object cleanup routine method is then called
        to make sure the object _child attribute is set to None

        Poll method source code: http://hg.python.org/cpython/file/ab05e7dd2788/Lib/multiprocessing/forking.py

        :param  timeout: time interval to poll the forked process status
        :type   timeout: float

        :returns: the forked process exit code status
        :rtype: int
        """
        super(ProcessOpen, self).wait(timeout)
        self.process.clean()

    def terminate(self):
        """Kills the running forked process.

        The method checks if the process is actually running, and
        will therefore send it a SIGTERM signal, and wait for it to
        exit before it returns.

        The process object cleanup routine method is then called
        to make sur the object _child attribute is set to None
        """
        super(ProcessOpen, self).terminate()
        self.process.clean()


class Process(object):
    """Process objects represent activity that is run in a child process

    :param  target: callable object to be invoked in the run method
    :type   target: callable

    :param  name: sets the process name
    :type   name: str

    :param  args: arguments to provide to the target
    :type   args: tuple

    :param  kwargs: keyword arguments to provide to the target
    :type   kwargs: dict
    """
    def __init__(self, target=None, name=None, parent=False, args=(), kwargs={}):
        self._current = get_current_process()
        self._parent_pid = self._current.pid
        self._child = None
        self._parent = None

        self.name = name or '{0} {1}'.format(self.__class__.__name__, os.getpid())
        self.daemonic = False
        self.target = target
        self.target_args = tuple(args)
        self.target_kwargs = dict(kwargs)

    def __str__(self):
        return '<{0}>'.format(self.name)

    def __repr__(self):
        return self.__str__()

    def create(self):
        """Method to be called when the process child is forked"""
        # Global try/except designed to catch
        # SystemExit and any uncaught exceptions
        # while run() method execution.
        try:
            self._current = self

            try:
                sys.stdin.close()
                sys.stdin = open(os.devnull)
            except (OSError, ValueError):
                pass

            # Run the process target and cleanup
            # the instance afterwards.
            try:
                self.run()
                exitcode = 0
            finally:
                self.clean()
        except SystemError as err:
            if not err.args:
                exitcode = 1
            elif isinstance(err.args[0], int):
                exitcode = err.args[0]
            else:
                sys.stderr.write(str(err.args[0]) + '\n')
                sys.stderr.flush()
                exitcode = 0 if isinstance(err.args[0], str) else 1
        except:
            exitcode = 1
            sys.stderr.write('Process {} with pid {}:\n'.format(self.name, self.pid))
            sys.stderr.flush()
            traceback.print_exc()

        return exitcode

    def clean(self):
        """Cleans up the object child process status"""
        self._current = get_current_process()
        self._child = None

    def run(self):
        """Runs the target with provided args and kwargs in a fork"""
        if self.target:
            self.target(*self.target_args, **self.target_kwargs)

    def start(self):
        """Starts the Process"""
        if os.getpid() != self._parent_pid:
            raise RuntimeError(
                "Can only start a process object created by current process"
            )
        if self._child is not None:
            raise RuntimeError("Cannot start a process twice")

        self._child = ProcessOpen(self)

    def join(self, timeout=None):
        """Awaits on Process exit

        :param  timeout: Time to wait for the process exit
        :type   timeout: float
        """
        if self._child is None:
            raise RuntimeError("Can only join a started process")

        self._child.wait(timeout)

    def terminate(self):
        """Forces the process to stop

        The method checks if the process is actually running, and
        will therefore send it a SIGTERM signal, and wait for it to
        exit before it returns.
        """
        if self._child is None:
            raise RuntimeError("Can only terminate a started process")

        self._child.terminate()

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

    @property
    def is_alive(self):
        if self._child is None or not self._child.pid:
            return False

        self._child.poll()

        return self._child.returncode is None

    @property
    def name(self):
        if not hasattr(self, '_name'):
            self._name = None

        return self._name

    @name.setter
    def name(self, value):
        if not isinstance(value, basestring):
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
