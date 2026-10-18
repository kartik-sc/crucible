"""Compatibility adapters for the frozen M2 Gateway interface."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

from .gateway import ModelGateway


@dataclass
class GatewayResult:
    text: str
    usage: dict = field(default_factory=dict)


class ModelGatewayAdapter:
    """Expose ModelGateway through the existing DevGateway call contract."""

    def __init__(self, gateway: ModelGateway):
        self._gateway = gateway

    async def call(self, role, messages, *, max_tokens, temp, seed=None, cache_prefix=None):
        result = await self._gateway.call(
            role,
            messages,
            max_tokens=max_tokens,
            temperature=temp,
            seed=seed,
        )
        return GatewayResult(result.text, vars(result.usage))

    async def aclose(self):
        await self._gateway.aclose()

    @property
    def usage(self):
        return self._gateway.usage

    def health(self):
        return []


class DevGateway:
    """Single-key development client retained for GATEWAY=dev."""

    def __init__(self):
        self._delegate = None
        if os.getenv("GATEWAY", "dev").strip().lower() == "pooled":
            from .config import build_gateway

            self._delegate = ModelGatewayAdapter(build_gateway())
        self.cfg = {
            "builder": (
                "https://api.groq.com/openai/v1",
                os.getenv("GROQ_BUILDER_MODEL", "qwen/qwen3-32b"),
                os.getenv("GROQ_API_KEY", ""),
            ),
            "breaker": (
                "https://generativelanguage.googleapis.com/v1beta/openai",
                os.getenv("AISTUDIO_BREAKER_MODEL", "gemma-3-27b-it"),
                os.getenv("GEMINI_API_KEY", ""),
            ),
        }

    async def call(self, role, messages, *, max_tokens, temp, seed=None, cache_prefix=None):
        if self._delegate is not None:
            return await self._delegate.call(
                role, messages, max_tokens=max_tokens, temp=temp, seed=seed,
                cache_prefix=cache_prefix,
            )
        base, model, key = self.cfg[role]
        if not key:
            env = "GROQ_API_KEYS" if role == "builder" else "AISTUDIO_API_KEYS"
            raise RuntimeError(f"no API key for {role}: set {env} on the server")
        body = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temp}
        if seed is not None:
            body["seed"] = seed
        if role == "builder" and model.startswith("qwen"):
            body["reasoning_format"] = "hidden"
        if role == "breaker":
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{base}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {key}"},
            )
            response.raise_for_status()
            payload = response.json()
        return GatewayResult(
            payload["choices"][0]["message"]["content"] or "",
            payload.get("usage", {}),
        )

    async def aclose(self):
        if self._delegate is not None:
            await self._delegate.aclose()

    @property
    def usage(self):
        return self._delegate.usage if self._delegate is not None else None
