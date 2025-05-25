import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import types
import base64
import pytest

from engine import CopyEngine


class DummyExec:
    async def quote(self, *a, **k):
        return {"data": [{"outAmount": 100, "inAmountAddress": "k"}]}

    async def swap_tx(self, *a, **k):
        return {"tx": base64.b64encode(b"abc").decode(), "exec_px": 1.01}

    async def create_limit(self, *a, **k):
        return {"limitOrderId": "id"}


@pytest.mark.asyncio
async def test_dry_run(monkeypatch, tmp_path):
    path = tmp_path / "j.csv"
    eng = CopyEngine([], dry=True, journal_path=str(path))
    eng.exec = DummyExec()
    monkeypatch.setattr(
        "engine.SLIPPAGE_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "engine.INCLUSION_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "engine.send_bundle", lambda *a, **k: (_ for _ in ()).throw(AssertionError())
    )
    monkeypatch.setattr("engine.add_priority_fee", lambda b: b)
    monkeypatch.setattr("engine.base58.b58decode", lambda b: b"")
    monkeypatch.setattr(
        "engine.Transaction.deserialize",
        lambda b: types.SimpleNamespace(
            sign=lambda *a, **k: None, serialize=lambda: b"tx"
        ),
    )
    monkeypatch.setattr("engine.Keypair.from_secret_key", lambda b: object())
    monkeypatch.setattr(
        "engine.Client",
        lambda *a, **k: types.SimpleNamespace(
            send_raw_transaction=lambda *a, **k: (_ for _ in ()).throw(AssertionError())
        ),
    )
    eng.pb.nav = lambda: 100.0
    eng.pb.pos = {}
    eng.pb.mark = {}
    eng.pb.update = lambda *a, **k: None
    eng.pb.update_peak = lambda *a, **k: None
    eng.pb.global_dd = lambda x: 0.0

    async def send(*a, **k):
        return None

    eng.notif.send = send

    async def size(*a, **k):
        return 10.0

    monkeypatch.setattr(eng, "_size", size)

    sig = await eng._execute_buy({"token": "TOK", "price": "1", "address": "A"})
    assert sig.startswith("SIM-")
    assert path.exists() and path.read_text()
