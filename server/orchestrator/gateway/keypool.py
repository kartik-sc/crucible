"""Health-tracked key pool with least-inflight selection.

This is what makes the 4-way breaker burst safe on a free tier: the four
concurrent calls each acquire the least-inflight, non-cooling key, so they spread
across the pool (~1.3 calls/key with 3 keys) instead of hammering one account.

Rotation rule lives here only in the form of cool-downs: a caller that hits a
retryable error releases the key with a cool-down; selection then skips it.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .errors import AllKeysCoolingError


def mask(key: str) -> str:
    """Never log a full key. Show provider-ish prefix + last 4."""
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


@dataclass
class KeyState:
    key: str
    inflight: int = 0
    consecutive_failures: int = 0
    cooldown_until: float = 0.0  # monotonic seconds
    last_used: float = 0.0

    @property
    def masked(self) -> str:
        return mask(self.key)


class KeyPool:
    """Thread-safe-within-event-loop pool. All mutation is guarded by a lock so
    concurrent acquire()/release() from the breaker fan-out stay consistent.
    """

    def __init__(self, keys: list[str], base_cooldown: float = 5.0, max_cooldown: float = 60.0):
        clean = [k.strip() for k in keys if k and k.strip()]
        if not clean:
            raise ValueError("KeyPool requires at least one non-empty key")
        self._states = [KeyState(k) for k in clean]
        self._lock = asyncio.Lock()
        self._base_cooldown = base_cooldown
        self._max_cooldown = max_cooldown

    def __len__(self) -> int:
        return len(self._states)

    async def acquire(self) -> KeyState:
        """Return the least-loaded available key, incrementing its inflight.

        Raises AllKeysCoolingError(wait=...) if every key is cooling; the caller
        decides whether to sleep and retry or give up.
        """
        async with self._lock:
            now = time.monotonic()
            available = [s for s in self._states if s.cooldown_until <= now]
            if not available:
                soonest = min(s.cooldown_until for s in self._states) - now
                raise AllKeysCoolingError(max(0.0, soonest))
            # least inflight -> fewest recent failures -> least-recently-used
            available.sort(key=lambda s: (s.inflight, s.consecutive_failures, s.last_used))
            chosen = available[0]
            chosen.inflight += 1
            chosen.last_used = now
            return chosen

    async def release(self, state: KeyState, *, success: bool, retry_after: float = 0.0,
                      long_cool: bool = False) -> None:
        """Return a key to the pool.

        success=True  -> clear failure streak.
        success=False -> apply a cool-down (provider Retry-After if given, else
                         exponential backoff on the failure streak). long_cool is
                         for auth failures: cool the key for the whole run-ish so a
                         bad key stops being retried.
        """
        async with self._lock:
            state.inflight = max(0, state.inflight - 1)
            if success:
                state.consecutive_failures = 0
                return
            state.consecutive_failures += 1
            if long_cool:
                cool = self._max_cooldown
            elif retry_after > 0:
                cool = min(retry_after, self._max_cooldown)
            else:
                # exponential backoff: base * 2^(fails-1), capped
                cool = min(self._base_cooldown * (2 ** (state.consecutive_failures - 1)),
                           self._max_cooldown)
            state.cooldown_until = time.monotonic() + cool

    async def snapshot(self) -> list[dict]:
        """Debug view for a /health endpoint or the budget meter UI."""
        async with self._lock:
            now = time.monotonic()
            return [
                {
                    "key": s.masked,
                    "inflight": s.inflight,
                    "failures": s.consecutive_failures,
                    "cooling_for": round(max(0.0, s.cooldown_until - now), 2),
                }
                for s in self._states
            ]
