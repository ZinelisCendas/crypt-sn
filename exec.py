from __future__ import annotations

import aiohttp
from typing import Any

from config import JUPITER_URL
from helpers import retry


class JupiterExec:
    def __init__(self, notif: Any | None = None):
        self.http = aiohttp.ClientSession()
        self.notif = notif

    async def quote(self, mint_in: str, mint_out: str, amount: int):
        url = f"{JUPITER_URL}/v6/quote?inputMint={mint_in}&outputMint={mint_out}&amount={amount}&slippageBps=50"

        async def go():
            async with self.http.get(url) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="jup.quote", notif=self.notif)

    async def swap_tx(self, route: dict):
        async def go():
            async with self.http.post(
                f"{JUPITER_URL}/v6/swap",
                json={"route": route, "userPublicKey": route["inAmountAddress"]},
            ) as r:
                r.raise_for_status()
                tx = await r.json()
                return tx["swapTransaction"]

        return await retry(go, name="jup.swap", notif=self.notif)

    async def create_limit(
        self, mint_in: str, mint_out: str, amount: int, limit_price: float
    ):
        url = f"{JUPITER_URL}/v6/limit"

        async def go():
            async with self.http.post(
                url,
                json={
                    "inputMint": mint_in,
                    "outputMint": mint_out,
                    "amount": amount,
                    "limitPrice": limit_price,
                    "clientId": "bot",
                },
            ) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="jup.limit", notif=self.notif)


async def get_priority_fee() -> int:
    """Return the estimated micro-lamports per compute unit for swaps."""

    url = "https://api.helius.xyz/v1/getPriorityFeeEstimate"
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{url}?transaction_type=swap") as r:
            if r.status == 429:
                return 1000
            data = await r.json()
            return int(data.get("priorityFeeEstimate", 1000))


async def add_priority_fee(tx_bytes: bytes) -> bytes:
    """Inject compute budget instructions into a serialized transaction."""

    from solders.compute_budget import (
        ID as CB_ID,
        set_compute_unit_limit,
        set_compute_unit_price,
    )
    from solders.instruction import CompiledInstruction
    from solders.message import Message
    from solders.transaction import VersionedTransaction

    fee = await get_priority_fee()
    tx = VersionedTransaction.from_bytes(tx_bytes)

    account_keys = list(tx.message.account_keys)
    if CB_ID not in account_keys:
        account_keys.append(CB_ID)
        extra_ro = 1
    else:
        extra_ro = 0
    cb_index = account_keys.index(CB_ID)

    price_ix = CompiledInstruction(cb_index, set_compute_unit_price(fee).data, b"")
    limit_ix = CompiledInstruction(
        cb_index, set_compute_unit_limit(1_400_000).data, b""
    )

    new_instructions = [price_ix, limit_ix, *tx.message.instructions]
    hdr = tx.message.header
    msg = Message.new_with_compiled_instructions(
        hdr.num_required_signatures,
        hdr.num_readonly_signed_accounts,
        hdr.num_readonly_unsigned_accounts + extra_ro,
        account_keys,
        tx.message.recent_blockhash,
        new_instructions,
    )
    new_tx = VersionedTransaction.populate(msg, tx.signatures)
    return bytes(new_tx)
