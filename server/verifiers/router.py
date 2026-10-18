"""Verifier Router (TR-18): dispatch each attack by evidence kind to an adapter.

  test / computation -> PyExec (M2)      claimCheck -> NLI (M2)

A timeout or adapter crash is INDETERMINATE (TRD §7): not landed, not scored,
logged, and the loop continues.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from contracts import Artifact, Attack, Verdict
from orchestrator.agents import VerifierAdapter, invoke

log = logging.getLogger(__name__)


@dataclass
class Ruling:
    verdict: Verdict
    settled: bool  # False = indeterminate; excluded from the score


class VerifierRouter:
    def __init__(self, adapters: dict[str, VerifierAdapter], timeout_sec: float) -> None:
        self.adapters = adapters
        self.timeout_sec = timeout_sec

    async def verify(self, artifact: Artifact, attack: Attack) -> Ruling:
        adapter = self.adapters.get(attack.evidence_kind)
        if adapter is None:
            return self._indeterminate(attack, f"no verifier for {attack.evidence_kind}")
        try:
            v = await asyncio.wait_for(invoke(adapter.verify, artifact, attack), self.timeout_sec)
            if not isinstance(v, Verdict):
                v = Verdict.model_validate({"attackId": attack.id, **v})
        except asyncio.TimeoutError:
            return self._indeterminate(attack, f"timeout after {self.timeout_sec}s")
        except Exception as exc:  # adapter bug must not kill the round
            log.exception("verifier crashed on %s", attack.id)
            return self._indeterminate(attack, f"verifier error: {exc}")
        v = v.model_copy(update={"attack_id": attack.id})
        if v.label in ("invalid", "indeterminate", "error"):
            # Proved nothing either way (bad attack, source 403, slow sandbox): shown, never scored.
            # Counting these as survived made runs 'converge' at 1.0 on zero evidence.
            return Ruling(verdict=v, settled=False)
        return Ruling(verdict=v, settled=True)

    @staticmethod
    def _indeterminate(attack: Attack, why: str) -> Ruling:
        log.warning("indeterminate %s: %s", attack.id, why)
        return Ruling(Verdict(attack_id=attack.id, landed=False, evidence=f"indeterminate: {why}"), settled=False)
