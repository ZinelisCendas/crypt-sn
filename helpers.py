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
