import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from engine import CopyEngine


@pytest.mark.asyncio
async def test_size_basic(monkeypatch):
    eng = CopyEngine([])

    async def atr(_, minutes=None):
        return 0.1

    monkeypatch.setattr("sizing.pyth_atr", atr)
    size = await eng._size("TOKEN", 1.0, 100.0)
    assert size == pytest.approx(25.0)


@pytest.mark.asyncio
async def test_size_negative_sharpe(monkeypatch):
    eng = CopyEngine([])

    async def atr(_, minutes=None):
        return 0.1

    monkeypatch.setattr("sizing.pyth_atr", atr)
    size = await eng._size("TOKEN", -1.0, 100.0)
    assert size == 0
