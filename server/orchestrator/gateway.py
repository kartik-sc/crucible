"""The Model Gateway SEAM. M1 (owner A) builds the real one; M2 only depends on this Protocol.

FakeGateway  -> unit tests, no network.
DevGateway   -> THROWAWAY OpenAI-compatible client so M2 can be smoke-tested live before
                M1's Gateway (key pools, rotation, failover) lands. Do not ship it into /run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Protocol

import httpx


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
    """role -> (base_url, model, key) from env. Both Groq and AI Studio expose OpenAI-style chat."""

    def __init__(self):
        self.cfg = {
            "builder": ("https://api.groq.com/openai/v1", os.getenv("GROQ_BUILDER_MODEL", "qwen/qwen3-32b"),
                        os.getenv("GROQ_API_KEY", "")),
            "breaker": ("https://generativelanguage.googleapis.com/v1beta/openai",
                        os.getenv("AISTUDIO_BREAKER_MODEL", "gemma-3-27b-it"),
                        os.getenv("GEMINI_API_KEY", "")),
        }

    async def call(self, role, messages, *, max_tokens, temp, seed=None, cache_prefix=None):
        base, model, key = self.cfg[role]
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temp}
        if seed is not None:
            body["seed"] = seed
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{base}/chat/completions", json=body,
                             headers={"Authorization": f"Bearer {key}"})
            r.raise_for_status()
            j = r.json()
        return GatewayResult(j["choices"][0]["message"]["content"] or "", j.get("usage", {}))
