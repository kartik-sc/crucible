"""Rotation + least-inflight proof — NO network, NO real keys.

Uses httpx.MockTransport to simulate a provider so we can assert:
  1. a 429 on the first-picked key rotates to a healthy key and still succeeds
  2. a 4-way concurrent fan-out spreads across more than one key
  3. a 400 (bug) fails fast WITHOUT rotating
  4. usage is accounted
  5. AI Studio requests never carry `seed` (it 400s there)

Run:  python test_rotation.py     (plain asserts; exits non-zero on failure)
  or  pytest test_rotation.py
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

import httpx

# allow `python test_rotation.py` from anywhere: put the package parent on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import AIStudioProvider, Endpoint, GroqProvider, KeyPool, ModelGateway  # noqa: E402
from gateway.errors import NonRetryableError  # noqa: E402


def _groq_ok(content: str = "ok") -> httpx.Response:
    body = {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    return httpx.Response(200, json=body)


def make_gateway(handler, keys, *, temp=0.2):
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    ep = Endpoint(provider=GroqProvider(), model="test-model",
                  pool=KeyPool(keys, base_cooldown=0.01, max_cooldown=0.05),
                  default_temperature=temp)
    return ModelGateway({"builder": ep}, client=client)


async def test_rotate_on_429():
    served: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        key = req.headers["Authorization"].removeprefix("Bearer ")
        served.append(key)
        if key == "k_bad":
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "rate"})
        return _groq_ok("hardened")

    gw = make_gateway(handler, ["k_bad", "k_ok1", "k_ok2"])
    res = await gw.builder([{"role": "user", "content": "hi"}], max_tokens=16)
    await gw.aclose()

    assert res.text == "hardened", res.text
    assert "k_bad" in served and len(served) >= 2, served
    assert served[-1] != "k_bad", served
    assert gw.usage.total().total_tokens == 15
    print("  [1] rotate-on-429              OK   served:", served)


async def test_concurrent_spread():
    served: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        key = req.headers["Authorization"].removeprefix("Bearer ")
        served.append(key)
        return _groq_ok()

    gw = make_gateway(handler, ["kA", "kB", "kC"])
    calls = [{"messages": [{"role": "user", "content": f"q{i}"}], "max_tokens": 8} for i in range(4)]
    # only 'builder' is wired in this test, so fan out builder calls concurrently
    results = await asyncio.gather(*(gw.builder(**c) for c in calls))
    await gw.aclose()

    assert all(r.text == "ok" for r in results)
    assert len(set(served)) >= 2, f"expected spread across keys, got {served}"
    print("  [2] concurrent spread          OK   distinct keys:", sorted(set(served)))


async def test_bug_fails_fast():
    served: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        served.append(req.headers["Authorization"].removeprefix("Bearer "))
        return httpx.Response(400, json={"error": "bad model id"})

    gw = make_gateway(handler, ["k1", "k2", "k3"])
    raised = False
    try:
        await gw.builder([{"role": "user", "content": "hi"}], max_tokens=16)
    except NonRetryableError:
        raised = True
    await gw.aclose()

    assert raised, "400 should raise NonRetryableError"
    assert len(served) == 1, f"400 must NOT rotate; served={served}"
    print("  [3] 400 fails fast (no rotate) OK   attempts:", len(served))


async def test_aistudio_no_seed():
    bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(req.content))
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "ok"}]}}],
            "usageMetadata": {"promptTokenCount": 1, "candidatesTokenCount": 1, "totalTokenCount": 2},
        })

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ep = Endpoint(provider=AIStudioProvider(), model="test-model",
                  pool=KeyPool(["kX"], base_cooldown=0.01, max_cooldown=0.05))
    gw = ModelGateway({"breaker": ep}, client=client)
    res = await gw.breaker([{"role": "user", "content": "hi"}], max_tokens=8, seed=3)
    await gw.aclose()

    assert res.text == "ok"
    assert "seed" not in bodies[0]["generationConfig"], bodies[0]
    assert bodies[0]["generationConfig"]["responseMimeType"] == "application/json", bodies[0]
    print("  [4] aistudio JSON mode         OK")


async def main():
    print("gateway rotation tests (mock transport, no network):")
    await test_rotate_on_429()
    await test_concurrent_spread()
    await test_bug_fails_fast()
    await test_aistudio_no_seed()
    print("ALL PASSED")


if __name__ == "__main__":
    asyncio.run(main())
