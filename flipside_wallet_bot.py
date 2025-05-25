from __future__ import annotations

import asyncio
from typing import Optional

from engine import CopyEngine
from flipside import Flipside
from config import FLIPSIDE_API_KEY, FLIPSIDE_API_URL


def _trending_wallets(limit: int = 10) -> list[str]:
    """Return top wallets ranked by 30-day PnL using the public tables."""
    client = Flipside(FLIPSIDE_API_KEY, FLIPSIDE_API_URL)
    sql = f"""
    SELECT
      wallet_address AS address
    FROM
      solana.core.fact_transactions
    WHERE
      block_timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 days'
    GROUP BY
      1
    ORDER BY
      SUM(pnl) DESC
    LIMIT {limit}
    """
    res = client.query(
        sql,
        max_age_minutes=60,
        cached=True,
        page_number=1,
        page_size=limit,
        timeout_minutes=2,
    )
    return [r[0] for r in (res.records or [])]


async def run_engine(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    seed = _trending_wallets()
    eng = CopyEngine(seed, dry=dry_run, ws_log=ws_log)
    await eng.run()


def main(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    try:
        asyncio.run(run_engine(ws_log, dry_run))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
