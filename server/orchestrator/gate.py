"""Heavy-Answer Gate (TR-2, TR-3): keep trivial answers out of the loop. No LLM.

Heaviness by domain:
  code    -> non-blank, non-comment lines
  factual -> claim (sentence) count
  math    -> derivation steps (lines / '='-separated steps)
"""

from __future__ import annotations

import re

from contracts import Domain

THRESHOLDS: dict[Domain, int] = {"code": 3, "factual": 2, "math": 2}


def heaviness(domain: Domain, content: str) -> int:
    if domain == "code":
        return sum(1 for ln in content.splitlines() if ln.strip() and not ln.strip().startswith("#"))
    if domain == "factual":
        return len([s for s in re.split(r"(?<=[.!?])\s+|\n+", content) if len(s.split()) >= 3])
    lines = [ln for ln in content.splitlines() if ln.strip()]
    return max(len(lines), content.count("="))


def is_heavy(domain: Domain, content: str) -> bool:
    return heaviness(domain, content) >= THRESHOLDS[domain]
