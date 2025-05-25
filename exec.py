from __future__ import annotations

import aiohttp
from typing import Any

from solders.keypair import Keypair
import base58

from config import JUPITER_URL, COOP_URL, PRIV_KEY
from helpers import retry


class JupiterExec:
    def __init__(self, notif: Any | None = None):
        self.http = aiohttp.ClientSession()
        self.notif = notif
        if PRIV_KEY:
            self.addr = str(Keypair.from_bytes(base58.b58decode(PRIV_KEY)).pubkey())
        else:
            self.addr = ""
        self._last: dict | None = None

    async def quote(self, mint_in: str, mint_out: str, amount: int):
        url = f"{COOP_URL}/defi/router/v1/sol/tx/get_swap_route"
        params = {
            "token_in_address": mint_in,
            "token_out_address": mint_out,
            "in_amount": str(amount),
            "from_address": self.addr,
            "slippage": "0.5",
            "swap_mode": "ExactIn",
        }

        async def go():
            async with self.http.get(url, params=params) as r:
                r.raise_for_status()
                data = await r.json()
                self._last = data.get("data", {})
                return {"data": [self._last.get("quote", {})]}

        return await retry(go, name="coop.quote", notif=self.notif)

    async def swap_tx(self, route: dict):
        if not self._last:
            raise RuntimeError("quote() must be called before swap_tx()")
        return self._last.get("raw_tx", {}).get("swapTransaction", "")

    async def submit_tx(self, signed_tx_b64: str, anti_mev: bool = False):
        url = f"{COOP_URL}/txproxy/v1/send_transaction"

        async def go():
            async with self.http.post(
                url,
                json={
                    "chain": "sol",
                    "signedTx": signed_tx_b64,
                    "isAntiMev": anti_mev,
                },
            ) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="coop.send", notif=self.notif)

    async def tx_status(self, tx_hash: str, last_valid_height: int):
        url = f"{COOP_URL}/defi/router/v1/sol/tx/get_transaction_status"
        params = {"hash": tx_hash, "last_valid_height": str(last_valid_height)}

        async def go():
            async with self.http.get(url, params=params) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="coop.status", notif=self.notif)

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

    async def close(self) -> None:
        await self.http.close()


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
