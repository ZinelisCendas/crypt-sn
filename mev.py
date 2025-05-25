import aiohttp
import base64

from config import JITO_RPC


async def send_bundle(tx_bytes: bytes) -> bool:
    """Submit a signed transaction to the Jito block engine.

    Returns ``True`` on HTTP 200, otherwise ``False``.
    """
    async with aiohttp.ClientSession() as s:
        async with s.post(
            JITO_RPC or "https://block-engine.jito.wtf/api/v1/transactions",
            json={"transaction": base64.b64encode(tx_bytes).decode()},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            return r.status == 200
