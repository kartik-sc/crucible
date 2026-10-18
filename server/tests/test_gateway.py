"""DevGateway stopgap-retry behavior (mock transport, no network, no real sleeps)."""
import asyncio

import httpx
import pytest

from orchestrator.gateway import DevGateway

_NOSLEEP = lambda _d: asyncio.sleep(0)  # noqa: E731


def _gateway(handler):
    return DevGateway(transport=httpx.MockTransport(handler), sleep=_NOSLEEP)


def test_retries_5xx_then_succeeds():
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        if seen["n"] <= 2:  # 503, 503, ...
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {"total_tokens": 7}})

    gw = _gateway(handler)
    res = asyncio.run(gw.call("builder", [{"role": "user", "content": "x"}], max_tokens=16, temp=0.2))
    assert res.text == "ok"
    assert res.usage == {"total_tokens": 7}
    assert seen["n"] == 3  # two retries then success


def test_400_fails_immediately():
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        return httpx.Response(400, json={"error": "bad request"})

    gw = _gateway(handler)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(gw.call("builder", [{"role": "user", "content": "x"}], max_tokens=16, temp=0.2))
    assert seen["n"] == 1  # no retry on a non-429 4xx


def test_gives_up_after_three_5xx():
    seen = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["n"] += 1
        return httpx.Response(503)

    gw = _gateway(handler)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(gw.call("breaker", [{"role": "user", "content": "x"}], max_tokens=16, temp=0.8))
    assert seen["n"] == 3  # 3 attempts total, then raise
