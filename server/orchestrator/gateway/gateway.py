"""ModelGateway — the only module that touches providers.

Responsibilities:
  - map a role ("builder" | "breaker") to a provider + model + key pool
  - rotate keys on 429 / 5xx / timeout (NOT on 4xx bugs)
  - spread the concurrent breaker fan-out least-inflight across the pool
  - enforce max_tokens / temperature / seed
  - account token usage for the live budget meter

Everything else in the system calls `await gateway.call(role, messages, ...)`
and never learns that keys, rotation, or providers exist.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from .errors import (
    AllKeysCoolingError,
    GatewayExhausted,
    KeyAuthError,
    NonRetryableError,
    RetryableError,
)
from .keypool import KeyPool
from .providers import CallResult, Message, Provider, Usage

log = logging.getLogger("crucible.gateway")


@dataclass
class Endpoint:
    provider: Provider
    model: str
    pool: KeyPool
    default_temperature: float | None = None


@dataclass
class UsageMeter:
    by_role: dict[str, Usage] = field(default_factory=dict)
    calls: int = 0

    def add(self, role: str, usage: Usage) -> None:
        self.by_role[role] = self.by_role.get(role, Usage()) + usage
        self.calls += 1

    def total(self) -> Usage:
        out = Usage()
        for u in self.by_role.values():
            out = out + u
        return out

    def summary(self) -> dict:
        t = self.total()
        return {
            "calls": self.calls,
            "total_tokens": t.total_tokens,
            "prompt_tokens": t.prompt_tokens,
            "completion_tokens": t.completion_tokens,
            "by_role": {r: vars(u) for r, u in self.by_role.items()},
        }


class ModelGateway:
    def __init__(self, endpoints: dict[str, Endpoint], *,
                 client: httpx.AsyncClient | None = None,
                 request_timeout: float = 60.0,
                 max_attempts_factor: int = 2,
                 cooling_wait_cap: float = 8.0):
        """
        endpoints           : {"builder": Endpoint(...), "breaker": Endpoint(...)}
        client              : inject an httpx.AsyncClient (tests pass a MockTransport)
        request_timeout      : per-request timeout
        max_attempts_factor  : retry budget = pool_size * factor (bounded)
        cooling_wait_cap     : max seconds to wait when the whole pool is cooling
        """
        self.endpoints = endpoints
        self._own_client = client is None
        self.client = client or httpx.AsyncClient(timeout=request_timeout)
        self.max_attempts_factor = max_attempts_factor
        self.cooling_wait_cap = cooling_wait_cap
        self.usage = UsageMeter()

    async def aclose(self) -> None:
        if self._own_client:
            await self.client.aclose()

    async def __aenter__(self) -> "ModelGateway":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    async def call(self, role: str, messages: list[Message], *,
                   max_tokens: int, temperature: float | None = None,
                   seed: int | None = None) -> CallResult:
        """Make one completion for `role`, rotating keys on transient failure.

        Raises:
          NonRetryableError  — a request/model bug (fail fast, do not rotate)
          GatewayExhausted   — retry budget spent (last_error attached)
        """
        if role not in self.endpoints:
            raise NonRetryableError(f"unknown role '{role}'")
        ep = self.endpoints[role]
        temp = temperature if temperature is not None else ep.default_temperature

        max_attempts = max(len(ep.pool) * self.max_attempts_factor, 2)
        attempts = 0
        last_err: Exception | None = None

        while attempts < max_attempts:
            try:
                state = await ep.pool.acquire()
            except AllKeysCoolingError as e:
                # every key cooling: wait a bounded moment then retry, else bail
                if attempts + 1 >= max_attempts:
                    raise GatewayExhausted(role, attempts, e) from e
                wait = min(e.wait, self.cooling_wait_cap)
                log.info("role=%s all keys cooling; waiting %.2fs", role, wait)
                await asyncio.sleep(max(wait, 0.05))
                attempts += 1
                last_err = e
                continue

            attempts += 1
            try:
                result = await ep.provider.complete(
                    self.client, state.key, ep.model, messages,
                    max_tokens=max_tokens, temperature=temp, seed=seed,
                )
                await ep.pool.release(state, success=True)
                self.usage.add(role, result.usage)
                return result

            except KeyAuthError as e:
                log.warning("role=%s key %s auth-failed; long-cooling", role, state.masked)
                await ep.pool.release(state, success=False, long_cool=True)
                last_err = e
                continue
            except RetryableError as e:
                log.info("role=%s key %s transient (%s); rotating", role, state.masked, e)
                await ep.pool.release(state, success=False, retry_after=e.retry_after)
                last_err = e
                continue
            except NonRetryableError:
                # a bug: identical on every key — release without cooling and fail
                await ep.pool.release(state, success=False)
                raise

        raise GatewayExhausted(role, attempts, last_err)

    # convenience wrappers -----------------------------------------------------

    async def builder(self, messages, *, max_tokens, temperature=None, seed=None) -> CallResult:
        return await self.call("builder", messages, max_tokens=max_tokens,
                               temperature=temperature, seed=seed)

    async def breaker(self, messages, *, max_tokens, temperature=None, seed=None) -> CallResult:
        return await self.call("breaker", messages, max_tokens=max_tokens,
                               temperature=temperature, seed=seed)

    async def breaker_fanout(self, calls: list[dict]) -> list[CallResult | Exception]:
        """Run N breaker calls concurrently. Each dict is kwargs for `breaker`.
        Returns results in order; failures are returned (not raised) so one bad
        breaker never sinks the round (mirrors Promise.allSettled).
        """
        async def one(kw):
            try:
                return await self.breaker(**kw)
            except Exception as e:  # noqa: BLE001 — deliberately captured per-call
                return e
        return await asyncio.gather(*(one(kw) for kw in calls))
