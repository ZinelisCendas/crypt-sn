from __future__ import annotations

import asyncio
from typing import Optional

from engine import CopyEngine
from flipside import Flipside
from flipside.errors import (
    QueryRunExecutionError,
    ApiError,
    ServerError,
)
import logging
from config import FLIPSIDE_API_KEY, FLIPSIDE_API_URL


def _trending_wallets(limit: int = 10) -> list[str]:
    """Return top wallets ranked by 30-day PnL.

    Uses ``solana.core.fact_transactions`` and the ``signer_address`` and ``pnl``
    columns documented in Flipside's public tables.
    """
    client = Flipside(FLIPSIDE_API_KEY, FLIPSIDE_API_URL)
    # signer_address → lowercase, Snowflake is case–insensitive if un-quoted.
    # fact_transactions keeps realised PnL in `pnl`;             ↙︎
    sql = f"""
      SELECT
        signer_address                 AS address,
        SUM(pnl)                       AS realised_pnl
      FROM  solana.core.fact_transactions
      WHERE block_timestamp >= CURRENT_TIMESTAMP - INTERVAL '30 day'
      GROUP BY 1
      ORDER BY realised_pnl DESC
      LIMIT {limit}
    """
    try:
        res = client.query(
            sql,
            max_age_minutes=60,
            cached=True,
            page_number=1,
            page_size=limit,
            timeout_minutes=2,
        )
    except (
        QueryRunExecutionError,
        ApiError,
        ServerError,
    ):  # pragma: no cover - logs only
        logging.getLogger(__name__).warning("trending query failed", exc_info=True)
        return []
    return [r[0] for r in (res.records or [])]


async def run_engine(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    seed = _trending_wallets() or [
        "11111111111111111111111111111111"
    ]  # dummy burn addr
    eng = CopyEngine(seed, dry=dry_run, ws_log=ws_log)
    await eng.run()


def main(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    try:
        asyncio.run(run_engine(ws_log, dry_run))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
