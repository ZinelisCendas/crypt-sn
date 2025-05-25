import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest
from exec import get_priority_fee


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def get(self, url, *a, **k):
        class Resp:
            async def json(self):
                return {"priorityFeeEstimate": 42}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp()


aiohttp = sys.modules["aiohttp"]
aiohttp.ClientSession = lambda: FakeSession()


@pytest.mark.asyncio
async def test_priority_fee():
    fee = await get_priority_fee()
    assert fee == 42
