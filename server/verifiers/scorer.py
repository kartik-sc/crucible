"""Scorer (TR-21, TR-22): verdicts -> robustness.

robustness = sum(survived_i * w_i) / sum(verified_i * w_i), over every settled
attack in the ledger, judged against the CURRENT version. A patch re-runs the
ledger, so prior landed breaks flip to survived and the dial climbs.
"""

from __future__ import annotations

from contracts import Score
from orchestrator.ledger import Entry

WEIGHTS = {"spec_gap": 1.5, "factual": 1.5, "numeric_type": 1.2, "boundary": 1.0}


def score(entries: list[Entry], round_no: int, new_breaks: int) -> Score:
    settled = [e for e in entries if e.settled]
    total = sum(WEIGHTS[e.attack.breaker] for e in settled)
    survived_w = sum(WEIGHTS[e.attack.breaker] for e in settled if not e.failing)
    landed = sum(1 for e in settled if e.failing)
    return Score(
        # No settled evidence = no earned trust.
        robustness=round(survived_w / total, 4) if total else 0.0,
        new_breaks=new_breaks,
        survived=len(settled) - landed,
        landed=landed,
        round=round_no,
    )
