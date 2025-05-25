import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from sizing import kelly_size


def test_kelly_monotonic():
    a = kelly_size(1000, 0.5, 2.0, 30)
    b = kelly_size(1000, 1.0, 2.0, 30)
    assert a < b


def test_kelly_negative():
    assert kelly_size(100, -0.1, 0.1, 10) == 0


def test_kelly_trade_weight():
    small = kelly_size(1000, 0.5, 1.0, 5)
    large = kelly_size(1000, 0.5, 1.0, 50)
    assert small < large
    assert small / large == pytest.approx(0.25, rel=0.2)
