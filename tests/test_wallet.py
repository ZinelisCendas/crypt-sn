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
            return WalletMetrics(
                addr, 1.5, 10.0, 0.6, 5, {"d1": 1, "d2": 1, "d3": 1, "d4": 1, "d5": 1}
            )
        return WalletMetrics(addr, 0.5, -1.0, 0.4, 2, {"d1": -1})

    monkeypatch.setattr(wa, "_one", fake_one)
    res = await wa.strong(["A", "B"])
    assert res == ["A"]


@pytest.mark.asyncio
async def test_cluster_prune(monkeypatch):
    wa = WalletAnalyzer()

    async def fake_one(addr: str):
        if addr == "A":
            return WalletMetrics(
                addr,
                1.6,
                10.0,
                0.6,
                5,
                {
                    "d1": 1,
                    "d2": 2,
                    "d3": 3,
                    "d4": 4,
                    "d5": 5,
                },
            )
        if addr == "B":
            return WalletMetrics(
                addr,
                1.2,
                9.0,
                0.6,
                5,
                {
                    "d1": 0.1619981,
                    "d2": 2.57616578,
                    "d3": 3.5398093,
                    "d4": 3.59331787,
                    "d5": 4.26678784,
                },
            )
        return WalletMetrics(
            addr,
            1.1,
            8.0,
            0.6,
            5,
            {
                "d1": 0.45128402,
                "d2": -1.68405999,
                "d3": -1.1601701,
                "d4": 1.35010682,
                "d5": -0.33128317,
            },
        )

    monkeypatch.setattr(wa, "_one", fake_one)
    res = await wa.strong(["A", "B", "C"])
    assert set(res) == {"A", "C"}
