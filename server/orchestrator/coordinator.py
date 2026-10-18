"""Coordinator ("queen"): parallel breaker fan-out, validation, dedup (TR-7, TR-8).

allSettled semantics: one breaker failing is reported, never fails the round.
Attacks are yielded as each breaker finishes, so the UI streams them live.
Dedup by signature against the Ledger happens HERE, before any verify spend.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import AsyncIterator, Union

from pydantic import ValidationError

from contracts import Attack, LedgerDigest
from orchestrator.agents import Breaker, invoke
from orchestrator.ledger import Ledger
from orchestrator.signatures import signature

log = logging.getLogger(__name__)

RATIONALE_MAX_CHARS = 160


@dataclass
class BreakerFailed:
    role: str
    message: str


@dataclass
class FanoutStats:
    proposed: int = 0
    invalid: int = 0
    duplicate: int = 0
    accepted: int = 0
    failed_roles: int = 0


class Coordinator:
    def __init__(self, breaker: Breaker, roles: tuple[str, ...], max_attacks: int) -> None:
        self.breaker = breaker
        self.roles = roles
        self.max_attacks = max_attacks

    async def fanout(
        self, spec: str, content: str, ledger: Ledger, round_no: int, stats: FanoutStats
    ) -> AsyncIterator[Union[Attack, BreakerFailed]]:
        digest = ledger.digest()
        tasks = {
            asyncio.create_task(self._run_role(role, spec, content, digest)): role for role in self.roles
        }
        try:
            for fut in asyncio.as_completed(tasks):
                role, raw, err = await fut
                if err is not None:
                    stats.failed_roles += 1
                    yield BreakerFailed(role, err)
                    continue
                for attack in self._accept(role, raw, ledger, round_no, stats):
                    yield attack
        finally:
            for t in tasks:
                t.cancel()

    async def _run_role(self, role: str, spec: str, content: str, digest: LedgerDigest):
        try:
            raw = await invoke(self.breaker.attack, spec, content, role, digest)
            return role, list(raw or []), None
        except Exception as exc:
            log.exception("breaker %s failed", role)
            return role, [], f"{type(exc).__name__}: {exc}"

    def _accept(self, role: str, raw: list, ledger: Ledger, round_no: int, stats: FanoutStats) -> list[Attack]:
        accepted: list[Attack] = []
        for item in raw[: self.max_attacks]:
            stats.proposed += 1
            try:
                data = item.to_json() if isinstance(item, Attack) else dict(item)
                data["breaker"] = role  # a breaker cannot claim another role's weight
                attack = Attack.model_validate(data)
            except (ValidationError, TypeError, ValueError):
                stats.invalid += 1  # TR-15: no evidence / malformed -> dropped
                continue
            sig = signature(attack)
            if sig in ledger:
                stats.duplicate += 1
                continue
            attack = attack.model_copy(
                update={
                    "signature": sig,
                    "id": "atk_" + sig.split(":", 1)[1][:8],
                    "rationale": attack.rationale[:RATIONALE_MAX_CHARS],
                }
            )
            ledger.add(attack, round_no)
            stats.accepted += 1
            accepted.append(attack)
        return accepted
