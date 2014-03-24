import pytest
import time
from decimal import Decimal

from pkit.utils import wait
from pkit.exceptions import TimeoutError


def test_wait_with_until_being_non_callable_raises():
    with pytest.raises(TypeError):
        wait(until="abc")


def test_wait_respects_timeout():
    a = 1
    raised = False

    timeout = Decimal(0.1)
    error_margin = timeout / Decimal(10)

    before_ts = time.time()
    try:
        wait(until=lambda v: v > 1, args=(a,), timeout=timeout)
    except TimeoutError:
        raised = True
    after_ts = time.time()

    assert raised is True
    assert abs((after_ts - before_ts) - 0.1) < error_margin
