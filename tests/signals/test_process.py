import mock

import pkit.process
from pkit import signals

from pkit.signals.base import call_signal_handler


def test_register_process():
    SIGCHLD = signals.constants.SIGCHLD
    pid = 42
    process = pkit.process.Process(target=lambda: None)
    process._child = lambda: None
    process._child.pid = pid

    vals = []
    process.on_sigchld = lambda *_: vals.append('OK')
    signals.process.register(
        SIGCHLD,
        process,
        process.on_sigchld)

    with mock.patch('os.waitpid', return_value=(pid, 0)):
        call_signal_handler(SIGCHLD)(SIGCHLD, None)

    assert vals == ['OK']


def test_register_two_process():
    SIGCHLD = signals.constants.SIGCHLD
    pid1 = 42
    pid2 = 1234

    process1 = pkit.process.Process(target=lambda: None)
    process1._child = lambda: None
    process1._child.pid = pid1

    process2 = pkit.process.Process(target=lambda: None)
    process2._child = lambda: None
    process2._child.pid = pid2

    vals = []

    process1.on_sigchld = lambda *_: vals.append(1)
    signals.process.register(
        SIGCHLD,
        process1,
        process1.on_sigchld)

    process2.on_sigchld = lambda *_: vals.append(2)
    signals.process.register(
        SIGCHLD,
        process2,
        process2.on_sigchld)

    with mock.patch('os.waitpid', return_value=(pid1, 0)):
        call_signal_handler(SIGCHLD)(SIGCHLD, None)

    with mock.patch('os.waitpid', return_value=(pid2, 0)):
        call_signal_handler(SIGCHLD)(SIGCHLD, None)

    assert vals == (1, 2)
