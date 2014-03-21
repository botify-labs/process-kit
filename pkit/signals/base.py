import signal
import collections

from pkit.signals import constants


__all__ = ['register', 'unregister']


SIGNAL_HANDLERS = collections.defaultdict(list)


def call_signal_handler(signum):
    def handle_signal(signum, sigframe):
        for handler in SIGNAL_HANDLERS[signum]:
            handler(signum, sigframe)

    return handle_signal


def register(signum, handler):
    if signum not in constants.SIGNAL_NUMBERS:
        raise ValueError('Unknow signal number {}'.format(signum))

    if not callable(handler):
        raise TypeError('handler must be callable')

    if signum not in SIGNAL_HANDLERS:
        signal.signal(signum, call_signal_handler(signum))

    SIGNAL_HANDLERS[signum].append(handler)


def unregister(signum, handler):
    if signum not in SIGNAL_HANDLERS:
        raise LookupError('signal number {} not found'.format(signum))

    handlers = SIGNAL_HANDLERS[signum]
    try:
        handlers.remove(handler)
    except ValueError:
        raise LookupError('handler {} not found for signal number {}'.format(
                          handler,
                          signum))
