from __future__ import annotations

import asyncio
import time
import math
from dataclasses import dataclass
from typing import Any, Dict, List
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from flipside import Flipside
from config import FLIPSIDE_API_KEY, FLIPSIDE_API_URL
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


class FlipsideAPI:  # minimal wrapper over official SDK
    def __init__(self, notif: Any | None = None):
        self.client = Flipside(FLIPSIDE_API_KEY, FLIPSIDE_API_URL)
        self.notif = notif

    async def _query(self, sql: str, *, max_age_minutes: int = 60):
        """Run a blocking SDK query in a thread."""
        return await asyncio.to_thread(
            self.client.query,
            sql,
            max_age_minutes=max_age_minutes,
            cached=True,
        )

    async def info(self, addr: str, tf: str = "30d"):
        """Return wallet profit info.

        Uses ``solana.core.fact_transactions`` and the ``signer_address`` and ``pnl``
        columns from Flipside's public tables.
        """
        sql = f"""
        WITH pnl AS (
          SELECT DATE_TRUNC('day', block_timestamp) AS day, SUM(pnl) AS daily_pnl
          FROM solana.core.fact_transactions
          WHERE signer_address = LOWER('{addr}')
            AND block_timestamp >= CURRENT_TIMESTAMP - INTERVAL '{tf}'
          GROUP BY 1
        )
        SELECT '{addr}' AS address,
               SUM(daily_pnl) AS total_realized_profit
        FROM pnl
        """

        async def run() -> dict | None:
            res = await self._query(sql, max_age_minutes=60)
            if res.records:
                row = res.records[0]
                return {
                    "data": {
                        "address": row[0],
                        "totalRealizedProfit": row[1],
                    }
                }
            return None

        return await retry(run, name="flipside.info", notif=self.notif)

    async def trades(self, addr: str, tf: str = "30d"):
        """Return per-transaction PnL series.

        Uses ``solana.core.fact_transactions`` with ``signer_address`` and ``pnl``
        columns from the Flipside dataset.
        """
        sql = f"""
        SELECT block_timestamp, pnl
        FROM solana.core.fact_transactions
        WHERE signer_address = LOWER('{addr}')
          AND block_timestamp >= CURRENT_TIMESTAMP - INTERVAL '{tf}'
        ORDER BY block_timestamp ASC
        """

        async def run() -> list:
            res = await self._query(sql, max_age_minutes=10)
            return [{"timestamp": row[0], "pnl": row[1]} for row in (res.records or [])]

        return await retry(run, name="flipside.trades", notif=self.notif)


class WalletAnalyzer:
    def __init__(self, tf: str = "30d", notif: Any | None = None):
        self.tf = tf
        self.api = FlipsideAPI(notif)

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
