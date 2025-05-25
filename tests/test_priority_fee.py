import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from exec import add_priority_fee, get_priority_fee


aiohttp = sys.modules["aiohttp"]


class FakeSession:
    def __init__(self, status: int = 200):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def get(self, url):
        status = self.status

        class Resp:
            def __init__(self, status: int):
                self.status = status

            async def json(self):
                return {"priorityFeeEstimate": 42}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp(status)


@pytest.mark.asyncio
async def test_priority_fee():
    aiohttp.ClientSession = lambda: FakeSession(200)
    fee = await get_priority_fee()
    assert fee == 42


@pytest.mark.asyncio
async def test_priority_fee_fallback():
    aiohttp.ClientSession = lambda: FakeSession(429)
    fee = await get_priority_fee()
    assert fee == 1000


@pytest.mark.asyncio
async def test_add_priority_fee(monkeypatch):
    async def pf():
        return 7

    monkeypatch.setattr("exec.get_priority_fee", pf)
    from solders.hash import Hash
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solders.instruction import Instruction
    from solders.message import Message
    from solders.transaction import VersionedTransaction

    payer = Keypair()
    ix = Instruction(Pubkey.default(), b"\x01", [])
    msg = Message.new_with_blockhash([ix], payer.pubkey(), Hash.new_unique())
    tx = VersionedTransaction(msg, [payer])
    out = await add_priority_fee(bytes(tx))
    new_tx = VersionedTransaction.from_bytes(out)
    assert (
        str(new_tx.message.program_id(0))
        == "ComputeBudget111111111111111111111111111111"
    )
    assert (
        new_tx.message.instructions[0].data == b"\x03\x07\x00\x00\x00\x00\x00\x00\x00"
    )
