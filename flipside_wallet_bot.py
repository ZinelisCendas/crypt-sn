from __future__ import annotations

import asyncio
from typing import Optional

from engine import CopyEngine
from flipside import Flipside
from config import FLIPSIDE_API_KEY, FLIPSIDE_API_URL


def _trending_wallets(limit: int = 10) -> list[str]:
    client = Flipside(FLIPSIDE_API_KEY, FLIPSIDE_API_URL)
    sql = "SELECT address FROM trending_wallets"
    res = client.query(sql, page_number=1, page_size=limit)
    addrs = [r[0] for r in (res.records or [])]
    current_page = 2
    total_pages = res.page.totalPages if res.page else 1
    while current_page <= total_pages and len(addrs) < limit:
        page_res = client.get_query_results(
            res.query_id, page_number=current_page, page_size=limit
        )
        addrs.extend(r[0] for r in (page_res.records or []))
        total_pages = page_res.page.totalPages
        current_page += 1
    return addrs[:limit]


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
