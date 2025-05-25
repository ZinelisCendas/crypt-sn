import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from exec import add_priority_fee, get_priority_fee


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def __init__(self, status=200):
        self._status = status

    def get(self, url):
        class Resp:
            status = self._status

            async def json(self):
                return {"priorityFeeEstimate": 42}

            def raise_for_status(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp()


aiohttp = sys.modules["aiohttp"]
aiohttp.ClientSession = lambda status=200: FakeSession(status)


@pytest.mark.asyncio
async def test_priority_fee():
    fee = await get_priority_fee()
    assert fee == 42


@pytest.mark.asyncio
async def test_priority_fee_429(monkeypatch):
    aiohttp.ClientSession = lambda status=429: FakeSession(status)
    fee = await get_priority_fee()
    assert fee == 1000


@pytest.mark.asyncio
async def test_add_priority_fee(monkeypatch):
    async def fake_fee():
        return 5000

    monkeypatch.setattr("exec.get_priority_fee", fake_fee)

    from solders.hash import Hash
    from solders.instruction import Instruction
    from solders.keypair import Keypair
    from solders.message import MessageV0
    from solders.pubkey import Pubkey
    from solders.transaction import VersionedTransaction
    from solders.compute_budget import ID as CB_ID

    payer = Keypair()
    ix = Instruction(Pubkey.default(), b"", [])
    msg = MessageV0.try_compile(payer.pubkey(), [ix], [], Hash.new_unique())
    tx = VersionedTransaction.populate(msg, [])
    res = await add_priority_fee(bytes(tx))
    new_tx = VersionedTransaction.from_bytes(res)
    price_ix = new_tx.message.instructions[0]
    limit_ix = new_tx.message.instructions[1]
    assert (
        new_tx.message.account_keys[price_ix.program_id_index] == CB_ID
        and price_ix.data[0] == 3
    )
    assert (
        new_tx.message.account_keys[limit_ix.program_id_index] == CB_ID
        and limit_ix.data[0] == 2
    )
