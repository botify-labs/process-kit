import os

import pkit.signals
from pkit.signals.base import SIGNAL_HANDLERS
from pkit.signals.registry import HandlerRegistry


def get_last_exited_pid():
    try:
        pid, _ = os.wait()
    except OSError:
        return None

    return pid


def get_registry_handler(signum, handlers=SIGNAL_HANDLERS):
    if signum not in handlers:
        return None

    for i in handlers[signum]:
        if isinstance(i, HandlerRegistry):
            registry_handler = i
            break

    return registry_handler


def register(signum, process, handler):
    registry_handler = get_registry_handler(signum)

    if registry_handler is None:
        registry_handler = HandlerRegistry(
            extract_from=lambda *_: get_last_exited_pid(),
            insert_with=lambda process: process.pid)
        pkit.signals.base.register(signum, registry_handler)

    registry_handler.register(process, handler)


def unregister(signum, process, handler):
    registry_handler = get_registry_handler(signum)

    if registry_handler is None:
        raise LookupError(
            'Handler {} for process {} and signal {} not found'.format(
                handler, process, signum))

    registry_handler.unregister(process, handler)
