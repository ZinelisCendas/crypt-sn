import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa: F401
import types
import base64
from solders.signature import Signature
import pytest
from engine import CopyEngine


@pytest.mark.asyncio
async def test_slippage_hist(monkeypatch):
    class DummyExec:
        async def quote(self, *a, **k):
            return {"data": [{"outAmount": 200, "inAmountAddress": "k"}]}

        async def swap_tx(self, *a, **k):
            return {"tx": base64.b64encode(b"abc").decode(), "exec_px": 20.04}

        async def create_limit(self, *a, **k):
            return {"limitOrderId": "abc"}

    eng = CopyEngine([])
    eng.exec = DummyExec()
    vals = []
    monkeypatch.setattr(
        "engine.SLIPPAGE_G", types.SimpleNamespace(observe=lambda v: vals.append(v))
    )
    monkeypatch.setattr(
        "engine.INCLUSION_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )

    async def dummy_pf(b):
        return b

    monkeypatch.setattr("engine.add_priority_fee", dummy_pf)
    monkeypatch.setattr("engine.base58.b58decode", lambda b: b"")

    class Tx:
        message = b""
        signatures: list = []

        def __bytes__(self):
            return b"tx"

    monkeypatch.setattr("engine.Transaction.from_bytes", lambda b: Tx())
    monkeypatch.setattr("engine.Transaction.populate", lambda msg, sigs: Tx())
    monkeypatch.setattr(
        "engine.Keypair.from_bytes",
        lambda b: types.SimpleNamespace(sign_message=lambda m: Signature.default()),
    )
    monkeypatch.setattr(
        "engine.Client",
        lambda *a, **k: types.SimpleNamespace(
            send_raw_transaction=lambda b: {"result": "sig"}
        ),
    )
    eng.pb.nav = lambda: 100.0
    eng.pb.pos = {}
    eng.pb.mark = {}
    eng.pb.update = lambda *a, **k: None
    eng.pb.update_peak = lambda *a, **k: None
    eng.pb.global_dd = lambda x: 0.0

    async def dummy_send(*a, **k):
        return None

    eng.notif.send = dummy_send

    async def size(*a, **k):
        return 10.0

    monkeypatch.setattr(eng, "_size", size)

    await eng._execute_buy({"token": "TOK", "price": "1"})

    assert vals and vals[-1] >= 20
