from __future__ import annotations

import asyncio
import logging
import time

import aiohttp
from typing import Any

from helpers import retry


class SolscanAPI:
    BASE = "https://public-api.solscan.io"

    def __init__(self, notif: Any | None = None):
        self.http = aiohttp.ClientSession()
        self.notif = notif

    async def holders(self, mint: str):
        async def go():
            async with self.http.get(
                f"{self.BASE}/token/holders?account={mint}&limit=50"
            ) as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="solscan.holders", notif=self.notif)

    async def meta(self, mint: str):
        async def go():
            async with self.http.get(f"{self.BASE}/token/meta?account={mint}") as r:
                r.raise_for_status()
                return await r.json()

        return await retry(go, name="solscan.meta", notif=self.notif)


class SafetyChecker:
    def __init__(self, sol: SolscanAPI, notif: Any | None = None):
        self.sol = sol
        self.notif = notif

    async def _solscan_ok(self, mint: str) -> bool:
        try:
            holders, meta = await asyncio.gather(
                self.sol.holders(mint), self.sol.meta(mint)
            )
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning("Solscan fail %s: %s", mint, exc)
            if self.notif:
                try:
                    await self.notif.send(f"Solscan error {mint}: {exc}")
                except Exception:  # noqa: BLE001
                    pass
            return False
        if not meta or meta.get("status") != "success":
            return False
        return len(holders.get("data", [])) >= 5

    async def rugcheck_pass(self, mint: str) -> bool:
        base = "https://api.rugcheck.xyz/v1"
        async with aiohttp.ClientSession() as s:

            async def liq_call():
                return await (
                    await s.get(f"{base}/liquidity/{mint}", timeout=10)
                ).json()

            async def vote_call():
                return await (await s.get(f"{base}/votes/{mint}", timeout=5)).json()

            liq = await retry(liq_call, name="rugcheck.liq", notif=self.notif)
            if liq["lp_owner_is_token_authority"] or liq["locked_pct"] < 70:
                return False
            vote = await retry(vote_call, name="rugcheck.vote", notif=self.notif)
            return vote.get("vote") != "rug"

    async def pumpfun_age_ok(self, mint: str) -> bool:
        info = await self.sol.meta(mint)
        launch_ts = info.get("data", {}).get("createdTime", 0)
        return time.time() - launch_ts > 7200

    async def dev_dump_ok(self, mint: str) -> bool:
        meta = await self.sol.meta(mint)
        auth = meta.get("data", {}).get("updateAuthority")
        if not auth:
            return True

        async def go():
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{self.sol.BASE}/account/transactions?account={auth}&limit=50"
                ) as r:
                    if r.status != 200:
                        return []
                    return await r.json()

        txs = await retry(go, name="solscan.devtx", notif=self.notif) or []
        sells = sum(1 for t in txs if t.get("type") == "Sell")
        buys = sum(1 for t in txs if t.get("type") == "Buy")
        return bool(buys) and sells / buys <= 2

    async def is_safe(self, mint: str) -> bool:
        solscan_ok = await self._solscan_ok(mint)
        if not solscan_ok:
            return False
        if not await self.rugcheck_pass(mint):
            return False
        if not await self.pumpfun_age_ok(mint):
            return False
        return await self.dev_dump_ok(mint)
