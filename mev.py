import aiohttp
import base64


async def send_bundle(tx_bytes: bytes):
    async with aiohttp.ClientSession() as s:
        await s.post(
            "https://block-engine.jito.wtf/api/v1/transactions",
            json={"transaction": base64.b64encode(tx_bytes).decode()},
            timeout=aiohttp.ClientTimeout(total=10),
        )
