from __future__ import annotations

import aiohttp
from typing import Any

from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from solana.transaction import Transaction

from config import HELIUS_API_KEY, JUPITER_URL
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
    headers = {"api-key": HELIUS_API_KEY}
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{url}?transaction_type=swap", headers=headers) as r:
            data = await r.json()
            return int(data.get("priorityFeeEstimate", 1000))


async def add_priority_fee(tx_bytes: bytes) -> bytes:
    lamports_per_cu = await get_priority_fee()
    try:
        tx = Transaction.deserialize(tx_bytes)
        ix_price = set_compute_unit_price(lamports_per_cu)
        ix_limit = set_compute_unit_limit(1_400_000)
        new_tx = Transaction().add(ix_limit, ix_price, *tx.instructions)
        return new_tx.serialize()
    except Exception:  # noqa: BLE001
        return tx_bytes
