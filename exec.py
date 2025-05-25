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

    async def cancel_limit(self, order_id: str):
        url = f"{JUPITER_URL}/v6/limit/cancel"

        async def go():
            async with self.http.post(url, json={"limitOrderId": order_id}) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="jup.cancel", notif=self.notif)


async def get_priority_fee() -> int:
    url = "https://api.helius.xyz/v1/getPriorityFeeEstimate"
    async with aiohttp.ClientSession() as s:
        async with s.get(f"{url}?transaction_type=swap") as r:
            data = await r.json()
            return int(data.get("priorityFeeEstimate", 1000))


async def add_priority_fee(tx_bytes: bytes) -> bytes:
    lamports_per_cu = await get_priority_fee()
    _ = lamports_per_cu  # placeholder for real mutation
    return tx_bytes
