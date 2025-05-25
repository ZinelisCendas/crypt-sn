from __future__ import annotations

import asyncio
import time
import math
from dataclasses import dataclass
from typing import Any, Dict, List

import aiohttp
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from gmgn import gmgn
import networkx as nx

from helpers import retry


@dataclass(slots=True)
class WalletMetrics:
    address: str
    sharpe: float
    realised: float
    win_rate: float
    trades: int
    daily: Dict[str, float]

    def is_strong(self) -> bool:
        return self.sharpe > 1.0 and self.win_rate * 100 >= 55 and self.realised > 0


def _lower_conf_sharpe(series: pd.Series, alpha: float = 0.05) -> float:
    sharpe = series.mean() / (series.std(ddof=1) or 1e-9)
    se = series.std(ddof=1) / math.sqrt(len(series))
    return sharpe - 1.645 * se


def _corr(a: Dict[str, float], b: Dict[str, float]) -> float:
    days = sorted(set(a) | set(b))
    v1 = [a.get(d, 0.0) for d in days]
    v2 = [b.get(d, 0.0) for d in days]
    n = len(v1)
    if n == 0:
        return 0.0
    mean1 = sum(v1) / n
    mean2 = sum(v2) / n
    var1 = sum((x - mean1) ** 2 for x in v1)
    var2 = sum((x - mean2) ** 2 for x in v2)
    if var1 == 0 or var2 == 0:
        return 0.0
    cov = sum((v1[i] - mean1) * (v2[i] - mean2) for i in range(n))
    return cov / (var1**0.5 * var2**0.5)


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
            return None
        series = pd.Series(list(pnl_by_day.values()))
        lb95 = _lower_conf_sharpe(series)

        cum = series.cumsum().to_numpy()
        X = np.arange(len(cum)).reshape(-1, 1)
        model = LinearRegression().fit(X, cum)
        slope, r2 = model.coef_[0], model.score(X, cum)
        if slope <= 0 or r2 < 0.4:
            return None

        win_rate = wins / max(1, len(trades))
        return WalletMetrics(
            info["data"]["address"],
            float(lb95),
            float(info["data"]["totalRealizedProfit"]),
            win_rate,
            len(trades),
            pnl_by_day,
        )

    async def strong(self, addrs: List[str]):
        res = await asyncio.gather(*(self._one(a) for a in addrs))
        metrics = [m for m in res if m and m.is_strong() and len(m.daily) >= 5]
        addr_map = {m.address: m for m in metrics}
        wl = list(addr_map)
        G = nx.Graph()
        G.add_nodes_from(wl)
        for i, w1 in enumerate(wl):
            for w2 in wl[i + 1 :]:
                if _corr(addr_map[w1].daily, addr_map[w2].daily) > 0.8:
                    G.add_edge(w1, w2)
        clusters = nx.algorithms.community.louvain_communities(G, resolution=1.0)
        selected = []
        for c in clusters:
            best = max(c, key=lambda w: addr_map[w].sharpe)
            selected.append(best)
        return selected
