import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import math
import pytest
from sizing import portfolio_vol


def manual_portfolio_vol(nav):
    alpha = 2 / (60 * 24 + 1)
    returns = [nav[i] / nav[i - 1] - 1 for i in range(1, len(nav))]
    rev = returns[::-1]
    sigma = math.sqrt(sum(alpha * (1 - alpha) ** i * r**2 for i, r in enumerate(rev)))
    return sigma * math.sqrt(60 * 24 * 365)


def test_portfolio_vol_zero():
    assert portfolio_vol([100]) == 0.0


def test_portfolio_vol_basic():
    nav = [100, 102, 104]
    expected = manual_portfolio_vol(nav)
    assert portfolio_vol(nav) == pytest.approx(expected)
