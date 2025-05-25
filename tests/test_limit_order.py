import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest

from exec import JupiterExec, JUPITER_URL


class FakeSession:
    def __init__(self):
        self.req = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def post(self, url, json):
        self.req = (url, json)

        class Resp:
            def raise_for_status(self):
                pass

            async def json(self):
                return {"limitOrderId": "x"}

            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *a):
                pass

        return Resp()


@pytest.mark.asyncio
async def test_cancel_limit():
    exec_ = JupiterExec()
    fake = FakeSession()
    exec_.http = fake
    resp = await exec_.cancel_limit("abc")
    assert resp == {"limitOrderId": "x"}
    assert fake.req == (f"{JUPITER_URL}/v6/limit/cancel", {"limitOrderId": "abc"})
