from __future__ import annotations
import asyncio
import logging


async def retry(
    coro_fn, *, retries: int = 3, timeout: float = 10.0, name: str = "req", notif=None
):
    """Retry an awaitable callable with exponential backoff."""
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            return await asyncio.wait_for(coro_fn(), timeout=timeout)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger(__name__).warning(
                "%s attempt %s failed: %s", name, attempt, exc
            )
            if attempt == retries:
                if notif is not None:
                    try:
                        await notif.send(f"{name} failed: {exc}")
                    except Exception:  # noqa: BLE001
                        pass
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)


def slippage_bps(executed_price: float, quote_price: float) -> float:
    """Return slippage in basis points given executed and quoted price."""
    if executed_price <= 0 or quote_price <= 0:
        return 0.0
    return abs(executed_price / quote_price - 1) * 10_000
