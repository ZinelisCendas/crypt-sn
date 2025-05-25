import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import types
import base64
import pytest

from engine import CopyEngine
from config import TAKE_PROFIT_PCT, SOL_MINT


class DummyExec:
    def __init__(self, calls):
        self.calls = calls

    async def quote(self, *a, **k):
        return {"data": [0]}

    async def swap_tx(self, *a, **k):
        return base64.b64encode(b"abc").decode()

    async def create_limit(self, mint_in, mint_out, amount, limit_price):
        self.calls["args"] = (mint_in, mint_out, amount, limit_price)
        return {"limitOrderId": "abc"}


@pytest.mark.asyncio
async def test_limit_order(monkeypatch):
    calls = {}
    eng = CopyEngine([])
    eng.exec = DummyExec(calls)
    monkeypatch.setattr(
        "engine.SLIPPAGE_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )
    monkeypatch.setattr(
        "engine.INCLUSION_G", types.SimpleNamespace(observe=lambda *a, **k: None)
    )

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
    monkeypatch.setattr("engine.Keypair.from_secret_key", lambda b: object())

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        def send_raw_transaction(self, tx):
            return {"result": "sig"}

    monkeypatch.setattr("engine.Client", FakeClient)

    async def dummy_size(*a, **k):
        return 1.0

    monkeypatch.setattr(eng, "_size", dummy_size)
    eng.pb.update_peak = lambda *a, **k: None
    eng.pb.global_dd = lambda x: 0.0

    async def dummy_send(*a, **k):
        return None

    eng.notif.send = dummy_send

    await eng._execute_buy({"token": "TOK", "price": "1"})

    assert calls["args"] == ("TOK", SOL_MINT, 1, 1 * (1 + TAKE_PROFIT_PCT / 100))
    assert eng.pb.pos["TOK"].limit_id == "abc"
