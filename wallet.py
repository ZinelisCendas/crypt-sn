from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, List

import aiohttp
import pandas as pd
from gmgn import gmgn

from helpers import retry


@dataclass(slots=True)
class WalletMetrics:
    address: str
    sharpe: float
    realised: float
    win_rate: float
    trades: int

    def is_strong(self) -> bool:
        return self.sharpe > 1.2 and self.win_rate * 100 >= 55 and self.realised > 0


class GmgnAPI:  # minimal wrapper
    def __init__(self, notif: Any | None = None):
        self.g = gmgn()
        self.http = aiohttp.ClientSession()
        self.notif = notif

    async def info(self, addr: str, tf: str = "30d"):
        loop = asyncio.get_running_loop()
        return await retry(
            lambda: loop.run_in_executor(None, self.g.getWalletInfo, addr, tf),
            name="gmgn.info",
            notif=self.notif,
        )

    async def trades(self, addr: str, tf: str = "30d"):
        url = f"https://gmgn.ai/stats/wallet/tx?address={addr}&period={tf}"

        async def go():
            async with self.http.get(url) as r:
                r.raise_for_status()
                return (await r.json()).get("data", [])

        return await retry(go, name="gmgn.trades", notif=self.notif)


class WalletAnalyzer:
    def __init__(self, tf: str = "30d", notif: Any | None = None):
        self.tf = tf
        self.api = GmgnAPI(notif)

    async def _one(self, addr: str):
        info, trades = await asyncio.gather(
            self.api.info(addr, self.tf), self.api.trades(addr, self.tf)
        )
        if not info or info.get("code") != 0:
            return None
        pnl_by_day: dict[str, float] = {}
        wins = 0
        for t in trades:
            day = time.strftime("%Y-%m-%d", time.gmtime(int(t["timestamp"]) / 1000))
            pnl_by_day[day] = pnl_by_day.get(day, 0) + float(t["pnl"])
            if float(t["pnl"]) > 0:
                wins += 1
        if len(pnl_by_day) < 2:
            sharpe = 0.0
        else:
            series = pd.Series(list(pnl_by_day.values()))
            sharpe = series.mean() / max(series.std(), 1e-6)
        win_rate = wins / max(1, len(trades))
        return WalletMetrics(
            info["data"]["address"],
            float(sharpe),
            float(info["data"]["totalRealizedProfit"]),
            win_rate,
            len(trades),
        )

    async def strong(self, addrs: List[str]):
        res = await asyncio.gather(*(self._one(a) for a in addrs))
        return [m.address for m in res if m and m.is_strong()]
