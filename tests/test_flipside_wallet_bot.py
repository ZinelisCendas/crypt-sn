import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import types
import pytest

import flipside_wallet_bot as fwb
from flipside.errors import QueryRunExecutionError


def test_trending_wallets_error(monkeypatch):
    class BadClient:
        def query(self, *a, **k):
            raise QueryRunExecutionError("fail")

    monkeypatch.setattr(fwb, "Flipside", lambda *a, **k: BadClient())
    assert fwb._trending_wallets() == []
