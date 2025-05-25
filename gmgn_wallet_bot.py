from __future__ import annotations

import asyncio
from typing import Optional

from engine import CopyEngine
from gmgn_fallback import gmgn


async def run_engine(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    seed = [w["address"] for w in gmgn().getTrendingWallets()["data"]][:10]
    eng = CopyEngine(seed, dry=dry_run, ws_log=ws_log)
    await eng.run()


def main(ws_log: Optional[str] = None, dry_run: bool = False) -> None:
    try:
        asyncio.run(run_engine(ws_log, dry_run))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
