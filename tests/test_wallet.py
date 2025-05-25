import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from wallet import WalletAnalyzer, WalletMetrics


@pytest.mark.asyncio
async def test_strong(monkeypatch):
    wa = WalletAnalyzer()

    async def fake_one(addr: str):
        if addr == "A":
            return WalletMetrics(addr, 1.5, 10.0, 0.6, 5)
        return WalletMetrics(addr, 0.5, -1.0, 0.4, 2)

    monkeypatch.setattr(wa, "_one", fake_one)
    res = await wa.strong(["A", "B"])
    assert res == ["A"]
