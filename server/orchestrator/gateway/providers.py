"""Provider adapters. Each normalizes one provider's HTTP API to CallResult and
classifies failures into the gateway error taxonomy. Keys are passed per-call by
the gateway (from the KeyPool); adapters are otherwise stateless.

Two providers:
  - GroqProvider     : Builder. OpenAI-compatible chat completions.
  - AIStudioProvider : Breaker swarm. Google Generative Language API.

Notes (learned from the live DevGateway run, 2026-10-18):
  - AI Studio returns 400 when `seed` is sent, so seed goes to Groq only.
  - Gemma on the Gemini API has no `system` role, so system text is folded into
    the first user turn (harmless for Gemini models too).
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from .errors import KeyAuthError, NonRetryableError, RetryableError


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.total_tokens + other.total_tokens,
        )


@dataclass
class CallResult:
    text: str
    usage: Usage
    provider: str
    model: str


Message = dict  # {"role": "system"|"user"|"assistant", "content": str}


def _retry_after(resp: httpx.Response) -> float:
    ra = resp.headers.get("retry-after")
    if not ra:
        return 0.0
    try:
        return float(ra)  # seconds form; HTTP-date form falls through to 0
    except ValueError:
        return 0.0


def _classify_status(resp: httpx.Response, provider: str) -> None:
    """Raise the right gateway error for a non-2xx response. 2xx returns None."""
    sc = resp.status_code
    if sc < 400:
        return
    body = resp.text[:400]
    if sc == 429:
        raise RetryableError(f"{provider} 429 rate limited: {body}", _retry_after(resp), sc)
    if sc in (401, 403):
        raise KeyAuthError(f"{provider} {sc} auth failed (bad/disabled key?): {body}", status=sc)
    if sc in (408, 500, 502, 503, 504):
        raise RetryableError(f"{provider} {sc} server error: {body}", _retry_after(resp), sc)
    # 400 / 404 / 422 / other 4xx: a request or model-id bug, identical on every key
    raise NonRetryableError(f"{provider} {sc} request error: {body}", sc)


class Provider:
    name = "base"

    async def complete(self, client: httpx.AsyncClient, key: str, model: str,
                       messages: list[Message], *, max_tokens: int,
                       temperature: float | None, seed: int | None) -> CallResult:
        raise NotImplementedError


class GroqProvider(Provider):
    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    async def complete(self, client, key, model, messages, *, max_tokens, temperature, seed):
        payload: dict = {"model": model, "messages": messages, "max_tokens": max_tokens}
        if temperature is not None:
            payload["temperature"] = temperature
        if seed is not None:
            payload["seed"] = seed
        if model.startswith("qwen"):
            payload["reasoning_format"] = "hidden"
        try:
            resp = await client.post(
                self.URL, json=payload,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        except httpx.TimeoutException as e:
            raise RetryableError(f"groq timeout: {e}")
        except httpx.TransportError as e:
            raise RetryableError(f"groq transport error: {e}")

        _classify_status(resp, self.name)
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise NonRetryableError(f"groq malformed response: {str(data)[:300]}")
        u = data.get("usage", {}) or {}
        usage = Usage(u.get("prompt_tokens", 0), u.get("completion_tokens", 0), u.get("total_tokens", 0))
        return CallResult(text=text, usage=usage, provider=self.name, model=model)


class AIStudioProvider(Provider):
    name = "aistudio"
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    @staticmethod
    def _to_contents(messages: list[Message]) -> list[dict]:
        system_text = ""
        contents: list[dict] = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_text += content + "\n\n"
            else:
                gem_role = "model" if role == "assistant" else "user"
                contents.append({"role": gem_role, "parts": [{"text": content}]})
        if system_text:
            for c in contents:
                if c["role"] == "user":
                    c["parts"][0]["text"] = system_text + c["parts"][0]["text"]
                    break
            else:
                contents.insert(0, {"role": "user", "parts": [{"text": system_text}]})
        return contents

    async def complete(self, client, key, model, messages, *, max_tokens, temperature, seed):
        url = f"{self.BASE}/models/{model}:generateContent"
        gen: dict = {"maxOutputTokens": max_tokens}
        if temperature is not None:
            gen["temperature"] = temperature
        gen["responseMimeType"] = "application/json"
        # `seed` intentionally NOT sent: AI Studio returned 400 on it in live testing.
        payload = {"contents": self._to_contents(messages), "generationConfig": gen}
        try:
            resp = await client.post(
                url, params={"key": key}, json=payload,
                headers={"Content-Type": "application/json"},
            )
        except httpx.TimeoutException as e:
            raise RetryableError(f"aistudio timeout: {e}")
        except httpx.TransportError as e:
            raise RetryableError(f"aistudio transport error: {e}")

        _classify_status(resp, self.name)
        data = resp.json()
        candidates = data.get("candidates") or []
        if not candidates:
            # blocked prompt / safety / empty — a content issue, not a key issue
            fb = data.get("promptFeedback", {})
            raise NonRetryableError(f"aistudio returned no candidates: {str(fb)[:300]}")
        try:
            parts = candidates[0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError):
            reason = candidates[0].get("finishReason", "unknown")
            raise NonRetryableError(f"aistudio no text (finishReason={reason})")
        um = data.get("usageMetadata", {}) or {}
        usage = Usage(
            um.get("promptTokenCount", 0),
            um.get("candidatesTokenCount", 0),
            um.get("totalTokenCount", 0),
        )
        return CallResult(text=text, usage=usage, provider=self.name, model=model)
