from __future__ import annotations

import aiohttp
from typing import Any

from solders.compute_budget import (
    ID as CB_ID,
    set_compute_unit_limit,
    set_compute_unit_price,
)
from solders.instruction import CompiledInstruction
from solders.message import Message, MessageHeader, MessageV0
from solders.transaction import VersionedTransaction

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
    url = "https://api.helius.xyz/v1/getPriorityFeeEstimate"

    async with aiohttp.ClientSession() as s:
        try:
            async with s.get(f"{url}?transaction_type=swap") as r:
                if r.status == 429:
                    return 1000
                r.raise_for_status()
                data = await r.json()
                return int(data.get("priorityFeeEstimate", 1000))
        except Exception:  # noqa: BLE001
            return 1000


async def add_priority_fee(tx_bytes: bytes) -> bytes:
    lamports_per_cu = await get_priority_fee()

    try:
        tx = VersionedTransaction.from_bytes(tx_bytes)
    except Exception:  # noqa: BLE001
        return tx_bytes

    msg = tx.message
    account_keys = list(msg.account_keys)
    header = msg.header
    if CB_ID not in account_keys:
        account_keys.append(CB_ID)
        header = MessageHeader(
            header.num_required_signatures,
            header.num_readonly_signed_accounts,
            header.num_readonly_unsigned_accounts + 1,
        )
    idx = account_keys.index(CB_ID)
    price_ix = set_compute_unit_price(lamports_per_cu)
    limit_ix = set_compute_unit_limit(1_400_000)
    comp_price = CompiledInstruction(idx, price_ix.data, bytes())
    comp_limit = CompiledInstruction(idx, limit_ix.data, bytes())
    new_instr = [comp_price, comp_limit] + list(msg.instructions)

    new_msg: Message | MessageV0
    if isinstance(msg, MessageV0):
        new_msg = MessageV0(
            header,
            account_keys,
            msg.recent_blockhash,
            new_instr,
            msg.address_table_lookups,
        )
    else:
        new_msg = Message.new_with_compiled_instructions(
            header.num_required_signatures,
            header.num_readonly_signed_accounts,
            header.num_readonly_unsigned_accounts,
            account_keys,
            msg.recent_blockhash,
            new_instr,
        )

    new_tx = VersionedTransaction.populate(new_msg, tx.signatures)
    return bytes(new_tx)
