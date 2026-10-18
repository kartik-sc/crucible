"""The Model Gateway SEAM. M1 (owner A) builds the real one; M2 only depends on this Protocol.

FakeGateway  -> unit tests, no network.
DevGateway   -> THROWAWAY OpenAI-compatible client so M2 can be smoke-tested live before
                M1's Gateway (key pools, rotation, failover) lands. Do not ship it into /run.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Protocol

import httpx

log = logging.getLogger(__name__)

RETRY_BACKOFF = (1.0, 2.0)  # seconds before attempt 2, then attempt 3 (3 attempts total)


def _retry_after(resp: httpx.Response, fallback: float) -> float:
    """Honor a numeric Retry-After header (seconds); fall back to the backoff schedule otherwise."""
    val = resp.headers.get("retry-after")
    if val:
        try:
            return max(0.0, float(val))
        except ValueError:
            pass  # HTTP-date form: not worth parsing for a stopgap; use the backoff
    return fallback


@dataclass
class GatewayResult:
    text: str
    usage: dict = field(default_factory=dict)


class Gateway(Protocol):
    async def call(self, role: str, messages: list[dict], *, max_tokens: int,
                   temp: float, seed: int | None = None,
                   cache_prefix: str | None = None) -> GatewayResult: ...


class FakeGateway:
    """responses: {"builder": [...], "breaker": [...]} (last item repeats) or fn(role, messages)->str."""

    def __init__(self, responses):
        self.responses, self.calls = responses, []

    async def call(self, role, messages, *, max_tokens, temp, seed=None, cache_prefix=None):
        self.calls.append({"role": role, "messages": messages, "max_tokens": max_tokens,
                           "temp": temp, "seed": seed})
        if callable(self.responses):
            return GatewayResult(self.responses(role, messages))
        queue = self.responses[role]
        text = queue.pop(0) if len(queue) > 1 else queue[0]
        return GatewayResult(text)


class DevGateway:
    """role -> (base_url, model, key) from env. Both Groq and AI Studio expose OpenAI-style chat.

    Stopgap retry (Ansh's pooled gateway replaces this): up to 3 attempts, retrying 429/5xx/timeouts
    with 1s then 2s backoff (honoring Retry-After); other 4xx fail immediately. `transport`/`sleep` are
    injectable for tests.
    """

    def __init__(self, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], Awaitable[None]] | None = None):
        self.cfg = {
            "builder": ("https://api.groq.com/openai/v1", os.getenv("GROQ_BUILDER_MODEL", "qwen/qwen3-32b"),
                        os.getenv("GROQ_API_KEY", "")),
            "breaker": ("https://generativelanguage.googleapis.com/v1beta/openai",
                        os.getenv("AISTUDIO_BREAKER_MODEL", "gemma-3-27b-it"),
                        os.getenv("GEMINI_API_KEY", "")),
        }
        self._transport = transport
        self._sleep = sleep or asyncio.sleep

    async def call(self, role, messages, *, max_tokens, temp, seed=None, cache_prefix=None):
        base, model, key = self.cfg[role]
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temp}
        if "groq.com" in base:
            # Groq's OpenAI layer supports `seed` (Google's rejects it: 400 Unknown name).
            if seed is not None:
                body["seed"] = seed
        else:
            # Google (Gemini/Gemma) OpenAI-compat: request JSON output for the breaker
            # (OpenAI-compat analog of responseMimeType application/json).
            body["response_format"] = {"type": "json_object"}

        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=60, transport=self._transport) as c:
            for attempt in range(3):  # up to 3 attempts total
                backoff = RETRY_BACKOFF[attempt] if attempt < len(RETRY_BACKOFF) else None
                try:
                    r = await c.post(url, json=body, headers=headers)
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    if backoff is None:
                        raise
                    log.warning("gateway %s: %s, retry %d/3 in %.1fs", role, type(exc).__name__, attempt + 2, backoff)
                    await self._sleep(backoff)
                    continue
                if r.status_code == 429 or r.status_code >= 500:  # retryable
                    if backoff is None:
                        r.raise_for_status()
                    delay = _retry_after(r, backoff)
                    log.warning("gateway %s: HTTP %d, retry %d/3 in %.1fs", role, r.status_code, attempt + 2, delay)
                    await self._sleep(delay)
                    continue
                r.raise_for_status()  # other 4xx -> fail immediately
                j = r.json()
                return GatewayResult(j["choices"][0]["message"]["content"] or "", j.get("usage", {}))
        raise RuntimeError("unreachable: retry loop exhausted without raising")
