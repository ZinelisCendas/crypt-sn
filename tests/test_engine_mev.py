import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from engine import CopyEngine
import types


class DummyExec:
    async def quote(self, *a, **k):
        return {"data": [0]}

    async def swap_tx(self, *a, **k):
        import base64

        return base64.b64encode(b"abc").decode()


@pytest.mark.asyncio
async def test_jito_fallback(monkeypatch):
    eng = CopyEngine([])
    eng.exec = DummyExec()
    monkeypatch.setattr("engine.JITO_RPC", "url")
    monkeypatch.setattr(
        "engine.SLIPPAGE_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "engine.INCLUSION_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )

    async def dummy_size(*a, **k):
        return 1.0

    monkeypatch.setattr(eng, "_size", dummy_size)

    async def dummy_pf(b):
        return b

    monkeypatch.setattr("engine.add_priority_fee", dummy_pf)
    monkeypatch.setattr("engine.base58.b58decode", lambda b: b"")

    class Tx:
        def sign(self, *a):
            pass

        def serialize(self):
            return b"tx_signed"

    monkeypatch.setattr("engine.Transaction.deserialize", lambda b: Tx())
    monkeypatch.setattr("engine.Keypair.from_bytes", lambda b: object())

    calls: dict[str, str | bytes] = {}

    async def send_bundle(tx: str) -> bool:
        calls["bundle"] = tx
        return False

    monkeypatch.setattr("engine.send_bundle", send_bundle)

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def send_raw_transaction(self, tx):
            calls["raw"] = tx
            return {"result": "sig"}

    monkeypatch.setattr("engine.Client", FakeClient)
    eng.pb.nav = lambda: 100.0
    eng.pb.pos = {}
    eng.pb.mark = {}
    eng.pb.update = lambda *a, **k: None
    eng.pb.update_peak = lambda *a, **k: None
    eng.pb.global_dd = lambda x: 0.0

    async def dummy_send(*a, **k):
        return None

    eng.notif.send = dummy_send

    await eng._execute_buy({"token": "ABC", "price": "1"})

    assert calls["bundle"] == "dHhfc2lnbmVk"
    assert calls["raw"] == b"tx_signed"
