import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
import base64
import types
from solders.signature import Signature
from engine import CopyEngine
from wallet import WalletMetrics


@pytest.mark.asyncio
async def test_size_basic(monkeypatch):
    eng = CopyEngine([])

    async def atr(*a, **k):
        return 0.1

    monkeypatch.setattr("engine.pyth_atr", atr)
    size = await eng._size("TOKEN", 1.0, 100.0)
    assert size == pytest.approx(25.0)


@pytest.mark.asyncio
async def test_size_negative_sharpe(monkeypatch):
    eng = CopyEngine([])

    async def atr(*a, **k):
        return 0.1

    monkeypatch.setattr("engine.pyth_atr", atr)
    size = await eng._size("TOKEN", -1.0, 100.0)
    assert size == 0


@pytest.mark.asyncio
async def test_execute_buy_uses_trades(monkeypatch):
    class DummyExec:
        async def quote(self, *a, **k):
            return {"data": [0]}

        async def swap_tx(self, *a, **k):
            return base64.b64encode(b"abc").decode()

        async def create_limit(self, *a, **k):
            return {"limitOrderId": "abc"}

    eng = CopyEngine([])
    eng.exec = DummyExec()
    eng.metrics["W"] = WalletMetrics("W", 1.0, 1.0, 0.6, 5, {"d": 1})
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

    called = {}

    async def dummy_size(self, token, sharpe, nav, trades=30):
        called["n"] = trades
        return 0.0

    monkeypatch.setattr(eng, "_size", dummy_size.__get__(eng, CopyEngine))

    await eng._execute_buy({"token": "TOK", "price": "1", "address": "W"})

    assert called["n"] == 5
