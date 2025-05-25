from __future__ import annotations

import math
import statistics
import time

import aiohttp
from typing import Any

from config import ATR_LOOKBACK_MIN, MAX_KELLY_F, PYTH_HIST_URL
from helpers import retry


async def pyth_atr(
    mint: str, minutes: int = ATR_LOOKBACK_MIN, notif: Any | None = None
) -> float:
    end = int(time.time())
    start = end - 60 * minutes
    url = f"{PYTH_HIST_URL}{mint}?start_time={start}&end_time={end}&interval=1"
    async with aiohttp.ClientSession() as s:

        async def go():
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                return [p[1] for p in data.get("prices", [])][-minutes:]

        prices = await retry(go, name="pyth.atr", notif=notif) or []
    if len(prices) < 2:
        return 0.05
    returns = [
        abs(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))
    ]
    return statistics.mean(returns) * math.sqrt(1440)


async def pyth_price(mint: str, notif: Any | None = None) -> float:
    end = int(time.time())
    start = end - 120
    url = f"{PYTH_HIST_URL}{mint}?start_time={start}&end_time={end}&interval=1"
    async with aiohttp.ClientSession() as s:

        async def go():
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                data = await r.json()
                return [p[1] for p in data.get("prices", [])]

        prices = await retry(go, name="pyth.price", notif=notif) or []
        return float(prices[-1]) if prices else 0.0


def kelly_size(nav: float, edge: float, vol: float) -> float:
    f = 0.5 * max(edge, 0.0)
    f = min(f, MAX_KELLY_F)
    stake_pct = f / max(vol, 1e-3)
    return max(0.0, min(stake_pct, 0.25)) * nav
