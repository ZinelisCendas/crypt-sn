import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from engine import CopyEngine


@pytest.mark.asyncio
async def test_size_basic(monkeypatch):
    eng = CopyEngine([])

    async def atr(*a, **k):
        return 0.1

    monkeypatch.setattr("engine.pyth_atr", atr)
    size = await eng._size("TOKEN", 1.0, 100.0, 30)
    assert size == pytest.approx(25.0)


@pytest.mark.asyncio
async def test_size_negative_sharpe(monkeypatch):
    eng = CopyEngine([])

    async def atr(*a, **k):
        return 0.1

    monkeypatch.setattr("engine.pyth_atr", atr)
    size = await eng._size("TOKEN", -1.0, 100.0, 30)
    assert size == 0


@pytest.mark.asyncio
async def test_size_trade_n(monkeypatch):
    eng = CopyEngine([])

    async def atr(*a, **k):
        return 1.0

    monkeypatch.setattr("engine.pyth_atr", atr)
    big = await eng._size("TOKEN", 0.5, 100.0, 30)
    small = await eng._size("TOKEN", 0.5, 100.0, 5)
    assert small < big
