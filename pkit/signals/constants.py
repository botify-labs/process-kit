import sys
import signal


__all__ = []  # Fill below


current_module = sys.modules[__name__]

SIGNALS = {k: v for k, v in vars(signal).iteritems() if
           k.startswith('SIG')}

SIGNAL_NUMBERS = SIGNALS.values()


def set_signals():
    for signame, signum in SIGNALS.iteritems():
        setattr(current_module, signame, signum)
        __all__.append(signame)

set_signals()
