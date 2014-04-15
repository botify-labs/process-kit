import pytest
import collections

from pkit.signals import base
from pkit.signals import constants


class TestBase(object):
    def setup_method(self):
        base.SIGNAL_HANDLERS = collections.defaultdict(list)

    def teardown_method(self):
        base.SIGNAL_HANDLERS = collections.defaultdict(list)


class TestCallSignalHandler(TestBase):
    def test_call_signal_handler(self):
        result = [None]

        def handler(signum, sigframe):
            result[0] = '{} works.'.format(signum)

        base.SIGNAL_HANDLERS[constants.SIGTERM] = [handler]
        base.call_signal_handler(constants.SIGTERM)(

            constants.SIGTERM, None)
        result[0] == '{} works.'.format(constants.SIGTERM)


class TestRegister(TestBase):
    def test_register_unknown_signum_raises(self):
        with pytest.raises(ValueError):
            base.register('aint no signal', lambda: None)

    def test_register_handler_with_invalid_type(self):
        with pytest.raises(TypeError):
            base.register(constants.SIGTERM, 'not a function')

    def test_register_one_handler(self):
        def handler(*args):
            return

        base.register(constants.SIGTERM, handler)
        base.SIGNAL_HANDLERS[constants.SIGTERM] == [handler]

    def test_register_two_handlers(self):
        def handler1(*args):
            return

        def handler2(*args):
            return

        base.register(constants.SIGTERM, handler1)
        base.register(constants.SIGTERM, handler2)

        base.SIGNAL_HANDLERS[constants.SIGTERM] = [handler1, handler2]


class TestUnregister(object):
    def setup_module(self):
        base.SIGNAL_HANDLERS = collections.defaultdict(list)

    def test_unregister_one_handler(self):
        def handler(*args):
            return

        base.register(constants.SIGTERM, handler)

        base.unregister(constants.SIGTERM, handler)
        base.SIGNAL_HANDLERS[constants.SIGTERM] == []

    def test_unregister_two_handlers(self):
        def handler1(*args):
            return

        def handler2(*args):
            return

        base.register(constants.SIGTERM, handler1)
        base.register(constants.SIGTERM, handler2)

        base.unregister(constants.SIGTERM, handler1)
        base.SIGNAL_HANDLERS[constants.SIGTERM] == [handler2]

        base.unregister(constants.SIGTERM, handler2)
        base.SIGNAL_HANDLERS[constants.SIGTERM] == []

    def test_unregister_signal_not_found(self):
        with pytest.raises(LookupError):
            base.unregister(constants.SIGTERM, 'test')

    def test_unregister_handler_not_found(self):
        def handler(*args):
            return

        base.register(constants.SIGTERM, handler)

        with pytest.raises(LookupError):
            base.unregister(constants.SIGTERM, 'test')
