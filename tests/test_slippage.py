import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
from helpers import slippage_bps
import pytest


def test_slippage_basic():
    assert slippage_bps(1.05, 1.0) == pytest.approx(500.0)


def test_slippage_zero():
    assert slippage_bps(0.0, 1.0) == 0.0
