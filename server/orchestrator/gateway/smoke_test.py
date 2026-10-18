"""Real smoke test — hits Groq + AI Studio with YOUR keys.

Setup:
    fill server/.env (GROQ_API_KEYS or GROQ_API_KEY, AISTUDIO_API_KEYS or
    GEMINI_API_KEY, GROQ_BUILDER_MODEL, AISTUDIO_BREAKER_MODEL)
    python smoke_test.py

It will:
    - call the Builder (Groq) once and check no <think> text leaks into content
    - call the Breaker (AI Studio) 4x concurrently (the real fan-out)
    - print text previews, per-role token usage, and the key-pool snapshot
Keys are never printed (pool snapshot is masked).
"""
from __future__ import annotations

import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# allow `python smoke_test.py` from anywhere: put the package parent on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gateway import build_gateway  # noqa: E402
from gateway.errors import ConfigError  # noqa: E402


def _load_env():
    if load_dotenv is None:
        print("note: python-dotenv not installed; relying on real env vars")
        return
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(here, "..", "..", ".env"),        # server/.env
        os.path.join(here, "..", "..", "..", ".env"),  # repo-root .env
    ):
        path = os.path.abspath(candidate)
        if os.path.exists(path):
            load_dotenv(path)
            print(f"loaded {path}")
            return
    print("no .env found in server/ or repo root; relying on real env vars")


async def main():
    _load_env()
    try:
        gw = build_gateway()
    except ConfigError as e:
        print("CONFIG ERROR:", e)
        sys.exit(1)

    ok = True
    try:
        print("\n--- Builder (Groq) ---")
        b = await gw.builder(
            [{"role": "user", "content": "Reply with exactly: BUILDER OK"}],
            max_tokens=64,
        )
        print("text   :", b.text.strip()[:120])
        print("usage  :", vars(b.usage))
        if "<think>" in b.text.lower():
            ok = False
            print("FAIL: <think> text leaked into builder content")

        print("\n--- Breaker swarm (AI Studio) x4 concurrent ---")
        calls = [
            {"messages": [{"role": "user", "content": f"Reply with exactly: BREAKER {i} OK"}],
             "max_tokens": 32}
            for i in range(4)
        ]
        results = await gw.breaker_fanout(calls)
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                ok = False
                print(f"breaker {i}: ERROR {type(r).__name__}: {r}")
            else:
                print(f"breaker {i}: {r.text.strip()[:60]}  usage={vars(r.usage)}")

        print("\n--- usage summary ---")
        print(gw.usage.summary())
        print("\n--- key pools (masked) ---")
        for role, ep in gw.endpoints.items():
            print(role, await ep.pool.snapshot())
    finally:
        await gw.aclose()

    print("\nSMOKE PASSED" if ok else "\nSMOKE FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
