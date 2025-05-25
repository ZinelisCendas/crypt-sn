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


def add_priority_fee(tx_bytes: bytes, lamports_per_cu: int = 1000) -> bytes:
    # placeholder – would insert ComputeBudget ix before first ix
    return tx_bytes
