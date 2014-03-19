import unittest
import collections

from pkit.signals import base


class TestBase(unittest.TestCase):
    def setUp(self):
        base.SIGNAL_HANDLERS = collections.defaultdict(list)


class TestCallSignalHandler(TestBase):
    def test_call_signal_handler(self):
        result = [None]

        def handler(string, *args):
            result[0] = '{} works.'.format(string)

        base.SIGNAL_HANDLERS[base.signal.SIGTERM] = [handler]
        base.call_signal_handler(base.signal.SIGTERM)('test')
        self.assertEquals(result[0], 'test works.')


class TestRegister(TestBase):
    def test_register_unknown_signum_raises(self):
        with self.assertRaises(ValueError):
            base.register('aint no signal', lambda: None)

    def test_register_handler_with_invalid_type(self):
        with self.assertRaises(TypeError):
            base.register(base.signal.SIGTERM, 'not a function')

    def test_register_one_handler(self):
        def handler(*args):
            return

        base.register(base.signal.SIGTERM, handler)
        self.assertEquals(base.SIGNAL_HANDLERS[base.signal.SIGTERM],
                          [handler])

    def test_register_two_handlers(self):
        def handler1(*args):
            return

        def handler2(*args):
            return

        base.register(base.signal.SIGTERM, handler1)
        base.register(base.signal.SIGTERM, handler2)

        self.assertEquals(base.SIGNAL_HANDLERS[base.signal.SIGTERM],
                          [handler1, handler2])
