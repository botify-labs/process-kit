import os

import pkit.signals
from pkit.signals.registry import HandlerRegistry


def register(signum, obj, handler):
    registry_handler = None
    for i in pkit.signals.base.SIGNAL_HANDLERS.values():
        if isinstance(i, HandlerRegistry):
            registry_handler = i
            break

    if registry_handler is None:
        registry_handler = HandlerRegistry(
            extract_from=lambda *_: os.waitpid()[0],
            insert_with=lambda process: process.pid)
        pkit.signals.base.register(signum, registry_handler)

    registry_handler.register(obj, handler)
