import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import types
import pytest

from wallet import FlipsideAPI


@pytest.mark.asyncio
async def test_info(monkeypatch):
    api = FlipsideAPI()

    def q(sql, **k):
        return types.SimpleNamespace(records=[["A", 1.0]])

    monkeypatch.setattr(api.client, "query", q)
    res = await api.info("A")
    assert res == {"data": {"address": "A", "totalRealizedProfit": 1.0}}


@pytest.mark.asyncio
async def test_trades(monkeypatch):
    api = FlipsideAPI()

    def q(sql, **k):
        return types.SimpleNamespace(records=[["t1", 1], ["t2", 2]])

    monkeypatch.setattr(api.client, "query", q)
    res = await api.trades("A")
    assert res == [{"timestamp": "t1", "pnl": 1}, {"timestamp": "t2", "pnl": 2}]
