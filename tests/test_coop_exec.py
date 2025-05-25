import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest

from exec import JupiterExec


@pytest.mark.asyncio
async def test_coop_quote_and_submit(monkeypatch):
    j = JupiterExec()

    def fake_get(url, params=None):
        class Resp:
            async def json(self):
                return {
                    "data": {
                        "quote": {"outAmount": 10},
                        "raw_tx": {"swapTransaction": "abc"},
                    }
                }

            def raise_for_status(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp()

    monkeypatch.setattr(j.http, "get", fake_get)

    res = await j.quote("A", "B", 1)
    assert res["data"]
    tx = await j.swap_tx(res["data"][0])
    assert tx == "abc"

    def fake_post(url, json=None):
        class Resp:
            async def json(self):
                return {"code": 0, "data": {"hash": "sig"}}

            def raise_for_status(self):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp()

    monkeypatch.setattr(j.http, "post", fake_post)
    resp = await j.submit_tx("abc", anti_mev=True)
    assert resp["code"] == 0
