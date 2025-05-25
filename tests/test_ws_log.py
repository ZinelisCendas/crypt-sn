import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest

from engine import CopyEngine


@pytest.mark.asyncio
async def test_ws_log(monkeypatch, tmp_path):
    log = tmp_path / "log.jsonl"
    log.write_text(
        '{"address":"A","token":"T","side":"buy","price":"1","timestamp":0}\n'
    )
    eng = CopyEngine(["A"], dry=True, ws_log=str(log))
    events = []

    async def dummy(ev):
        events.append(ev)

    monkeypatch.setattr(eng, "_execute_buy", dummy)

    async def safe(*a, **k):
        return True

    monkeypatch.setattr(eng.safe, "is_safe", safe)
    await eng._wallet_stream()
    assert events and events[0]["token"] == "T"
