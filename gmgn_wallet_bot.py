from __future__ import annotations

import asyncio

from engine import CopyEngine
from gmgn import gmgn


async def cli() -> None:
    seed = [w["address"] for w in gmgn().getTrendingWallets()["data"]][:10]
    eng = CopyEngine(seed)
    await eng.run()


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
