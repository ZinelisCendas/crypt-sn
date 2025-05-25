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


def calc_report(df):
    """Return CAGR, Sharpe and max drawdown from a journal DataFrame."""
    nav = [float(x) for x in df["nav_after"]]
    ts = [float(x) for x in df["ts"]]
    if len(nav) < 2:
        return 0.0, 0.0, 0.0
    years = (ts[-1] - ts[0]) / 31_536_000 or 1e-9
    cagr = (nav[-1] / nav[0]) ** (1 / years) - 1
    rets = [(nav[i] / nav[i - 1]) - 1 for i in range(1, len(nav))]
    if rets:
        mean_r = sum(rets) / len(rets)
        var = sum((r - mean_r) ** 2 for r in rets) / len(rets)
        sharpe = (mean_r / (var**0.5 or 1e-9)) * (252**0.5)
    else:
        sharpe = 0.0
    peak = nav[0]
    max_dd = 0.0
    for v in nav:
        if v > peak:
            peak = v
        dd = 1 - v / peak
        if dd > max_dd:
            max_dd = dd
    return float(cagr), float(sharpe), float(max_dd)
