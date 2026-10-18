"""The M1 <-> M2 seam (CONTRACTS §2). M2 implements these; M1 only calls them.

Methods may be sync or async — the engine awaits whichever it gets.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Protocol, Union

from contracts import Artifact, Attack, Domain, LandedBreak, LedgerDigest

MaybeAwaitable = Union[Any, Awaitable[Any]]


class Builder(Protocol):
    def generate(self, spec: str, domain: Domain) -> MaybeAwaitable:
        """-> BuildResult {content, assumptions}"""

    def patch(self, artifact: Artifact, breaks: list[LandedBreak]) -> MaybeAwaitable:
        """Delta-only (TR-12): `breaks` holds ONLY currently failing attacks + actuals. -> str"""


class Breaker(Protocol):
    def attack(self, spec: str, content: str, weakness_class: str, digest: LedgerDigest) -> MaybeAwaitable:
        """-> list[Attack | dict]. One scaffold; the role is `weakness_class`."""


class VerifierAdapter(Protocol):
    def verify(self, artifact: Artifact, attack: Attack) -> MaybeAwaitable:
        """-> Verdict. Execution or entailment only — never an LLM opinion."""


@dataclass
class Agents:
    builder: Builder
    breaker: Breaker
    # evidence kind -> adapter: {"test": pyexec, "computation": pyexec, "claimCheck": nli}
    verifiers: dict[str, VerifierAdapter]
    gateway: Any = None  # optional; exposes health()/usage for /health and /usage


async def invoke(fn: Callable[..., Any], *args: Any) -> Any:
    """Await async agent methods; run sync ones in a thread so they never block the stream."""
    if inspect.iscoroutinefunction(fn):
        return await fn(*args)
    result = await asyncio.to_thread(fn, *args)
    return await result if inspect.isawaitable(result) else result
