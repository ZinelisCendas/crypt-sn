import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import conftest  # noqa:F401
import pytest

from mev import send_bundle


class FakeSession:
    def __init__(self, status: int):
        self.status = status

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    def post(self, *a, **k):
        class Resp:
            def __init__(self, status: int):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                pass

        return Resp(self.status)


aiohttp = sys.modules["aiohttp"]


@pytest.mark.asyncio
async def test_send_bundle_success(monkeypatch):
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession(200))
    assert await send_bundle("dHg=")


@pytest.mark.asyncio
async def test_send_bundle_fail(monkeypatch):
    monkeypatch.setattr(aiohttp, "ClientSession", lambda: FakeSession(500))
    assert not await send_bundle("dHg=")
