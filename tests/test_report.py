import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pandas as pd
from helpers import calc_report


def test_calc_report():
    df = pd.DataFrame(
        {
            "ts": [0, 86400],
            "address": ["a", "a"],
            "token": ["t", "t"],
            "side": ["buy", "sell"],
            "qty": [1, 1],
            "price": [1, 1],
            "nav_after": [100, 110],
        }
    )
    cagr, sharpe, dd = calc_report(df)
    assert cagr > 0
    assert dd == 0
