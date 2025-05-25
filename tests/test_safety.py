import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from safety import SafetyChecker


@pytest.mark.asyncio
async def test_is_safe(monkeypatch):
    sc = SafetyChecker(None, None)

    async def ok(_):
        return True

    async def bad(_):
        return False

    monkeypatch.setattr(sc, "_solscan_ok", ok)
    monkeypatch.setattr(sc, "rugcheck_pass", ok)
    assert await sc.is_safe("M")

    monkeypatch.setattr(sc, "rugcheck_pass", bad)
    assert not await sc.is_safe("M")
