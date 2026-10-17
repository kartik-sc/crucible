"""Scripted fake agents: the real engine, no keys, deterministic.

Each domain has one planted-flaw scenario (the same shape as M2's demo
artifacts). Used by `/mock/run` (unblocks M3), by `CRUCIBLE_AGENTS=fake`, and by
tests. The code-domain verifier really executes the scripted (trusted) versions.
"""

from __future__ import annotations

import ast
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from contracts import Artifact, Attack, BuildResult, Domain, LandedBreak, LedgerDigest, Verdict
from orchestrator.agents import Agents

# ---- scenarios -------------------------------------------------------------------

CODE_V0 = '''def fib(n):
    """Return the nth Fibonacci number, n >= 0."""
    if n < 2:
        return 1
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''

CODE_V1 = '''def fib(n):
    """Return the nth Fibonacci number, n >= 0."""
    if not isinstance(n, int) or isinstance(n, bool):
        raise TypeError("n must be an int")
    if n < 0:
        raise ValueError("n must be >= 0")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
'''

MATH_V0 = """Leg 1: 120 km in 2 h -> 60 km/h
Leg 2: 120 km in 1 h -> 120 km/h
Average speed = (60 + 120) / 2 = 90 km/h"""

MATH_V1 = """Leg 1: 120 km in 2 h -> 60 km/h
Leg 2: 120 km in 1 h -> 120 km/h
Average speed = total distance / total time = 240 / 3 = 80 km/h"""

FACT_V0 = (
    "JWST launched on 25 December 2021 aboard an Ariane 5 rocket. "
    "Its primary mirror is 6.5 m across, built from 18 gold-coated beryllium segments. "
    "It orbits the Earth at an altitude of about 1.5 million km."
)

FACT_V1 = (
    "JWST launched on 25 December 2021 aboard an Ariane 5 rocket. "
    "Its primary mirror is 6.5 m across, built from 18 gold-coated beryllium segments. "
    "It orbits the Sun near the Sun-Earth L2 point, about 1.5 million km from Earth."
)


def _t(inp: str, exp: str, why: str) -> dict:
    return {"rationale": why, "test": {"input": inp, "expected": exp}}


def _c(expr: str, exp: str, why: str) -> dict:
    return {"rationale": why, "computation": {"expr": expr, "expected": exp}}


def _f(claim: str, query: str, why: str) -> dict:
    return {"rationale": why, "claimCheck": {"claim": claim, "sourceQuery": query}}


@dataclass
class Scenario:
    spec: str
    assumptions: list[str]
    versions: list[str]
    # round -> role -> raw attacks (dicts, like a parsed LLM response)
    attacks: dict[int, dict[str, list[dict]]]
    oracle: Callable[[int, Attack], Verdict]
    raise_on: set[str] = field(default_factory=set)  # roles whose breaker "crashes"


def _code_oracle(versions: list[str]):
    def oracle(v: int, a: Attack) -> Verdict:
        ns: dict = {}
        exec(versions[v], ns)  # scripted, trusted content only
        arg = ast.literal_eval(a.test.input)
        try:
            actual = repr(ns["fib"](arg))
        except Exception as exc:
            actual = f"raises {type(exc).__name__}"
        exp = a.test.expected.strip()
        if not exp.startswith("raises "):
            exp = repr(ast.literal_eval(exp))
        landed = actual != exp
        return Verdict(
            attack_id=a.id,
            landed=landed,
            actual=actual,
            evidence=f"fib({a.test.input}): expected {exp}, got {actual}" if landed else f"fib({a.test.input}) == {actual}",
        )

    return oracle


def _table_oracle(table: dict[str, Callable[[int], tuple[bool, str, str]]]):
    def oracle(v: int, a: Attack) -> Verdict:
        key = a.computation.expr if a.computation else a.claim_check.claim
        landed, actual, evidence = table[key](v)
        return Verdict(attack_id=a.id, landed=landed, actual=actual, evidence=evidence)

    return oracle


SCENARIOS: dict[Domain, Scenario] = {
    "code": Scenario(
        spec="Return the nth Fibonacci number, n >= 0.",
        assumptions=["n is an int"],
        versions=[CODE_V0, CODE_V1],
        attacks={
            1: {
                "boundary": [_t("0", "0", "n=0 edge case"), _t("1", "1", "n=1 edge case")],
                "numeric_type": [_t("2.5", "raises TypeError", "float input"), _t("True", "raises TypeError", "bool is an int subclass")],
                "spec_gap": [_t("-1", "raises ValueError", "spec says n >= 0"), _t(" 0 ", "0", "zero, again")],  # dup of boundary
                "factual": [],
            },
            2: {
                "boundary": [_t("2", "1", "first computed term"), _t("30", "832040", "larger n")],
                "numeric_type": [_t("100", "354224848179261915075", "big-int growth")],
                "spec_gap": [_t("-1", "raises ValueError", "negative, again"), _t("-5", "raises ValueError", "more negatives")],
                "factual": [],
            },
        },
        oracle=_code_oracle([CODE_V0, CODE_V1]),
    ),
    "math": Scenario(
        spec="A car drives 120 km in 2 hours, then 120 km in 1 hour. What is its average speed?",
        assumptions=["constant speed within each leg"],
        versions=[MATH_V0, MATH_V1],
        attacks={
            1: {
                "boundary": [_c("120/2", "60", "leg 1 speed")],
                "numeric_type": [_c("(120+120)/(2+1)", "80", "average = distance / time")],
                "spec_gap": [_c("120/1", "120", "leg 2 speed")],
                "factual": [],
            },
            2: {
                "boundary": [_c("240 / 3", "80", "re-derive total")],
                "numeric_type": [_c("2/(1/60+1/120)", "80", "harmonic mean check")],
                "spec_gap": [],
                "factual": [],
            },
        },
        oracle=_table_oracle(
            {
                "120/2": lambda v: (False, "60", "120/2 = 60 matches leg 1"),
                "120/1": lambda v: (False, "120", "120/1 = 120 matches leg 2"),
                "(120+120)/(2+1)": lambda v: (
                    (True, "90", "computed 80, answer states 90") if v == 0 else (False, "80", "computed 80 = answer")
                ),
                "240 / 3": lambda v: (v == 0, "80", "computed 80"),
                "2/(1/60+1/120)": lambda v: (v == 0, "80.0", "harmonic mean of equal-distance legs = 80"),
            }
        ),
    ),
    "factual": Scenario(
        spec="Summarize the key facts about the James Webb Space Telescope.",
        assumptions=[],
        versions=[FACT_V0, FACT_V1],
        attacks={
            1: {
                "boundary": [],
                "numeric_type": [_f("JWST's primary mirror has 18 segments", "JWST mirror segments", "count check")],
                "spec_gap": [],
                "factual": [
                    _f("JWST launched in December 2021", "JWST launch date", "date check"),
                    _f("JWST orbits the Earth", "JWST orbit location", "orbit check"),
                ],
            },
            2: {
                "boundary": [],
                "numeric_type": [],
                "spec_gap": [],
                "factual": [_f("JWST operates near the Sun-Earth L2 point", "JWST L2 orbit", "re-check orbit")],
            },
        },
        oracle=_table_oracle(
            {
                "JWST's primary mirror has 18 segments": lambda v: (
                    False, "SUPPORTED", "SUPPORTED: \"...18 hexagonal mirror segments...\" (nasa.gov)"
                ),
                "JWST launched in December 2021": lambda v: (
                    False, "SUPPORTED", "SUPPORTED: \"launched December 25, 2021\" (nasa.gov)"
                ),
                "JWST orbits the Earth": lambda v: (
                    (True, "CONTRADICTED", "CONTRADICTED: \"orbits the Sun at the second Lagrange point (L2)\" (esa.int)")
                    if v == 0
                    else (False, "SUPPORTED", "claim removed; L2 orbit now SUPPORTED (esa.int)")
                ),
                "JWST operates near the Sun-Earth L2 point": lambda v: (
                    v == 0, "SUPPORTED", "SUPPORTED: \"orbits the Sun at L2, 1.5 million km from Earth\" (esa.int)"
                ),
            }
        ),
    ),
}


# ---- fake agents --------------------------------------------------------------------

class FakeBuilder:
    def __init__(self, sc: Scenario, delay: float, never_fixes: bool = False) -> None:
        self.sc, self.delay, self.never_fixes = sc, delay, never_fixes

    async def generate(self, spec: str, domain: Domain) -> BuildResult:
        await asyncio.sleep(self.delay)
        return BuildResult(content=self.sc.versions[0], assumptions=self.sc.assumptions)

    async def patch(self, artifact: Artifact, breaks: list[LandedBreak]) -> str:
        await asyncio.sleep(self.delay)
        if self.never_fixes:
            return artifact.content
        idx = self.sc.versions.index(artifact.content)
        return self.sc.versions[min(idx + 1, len(self.sc.versions) - 1)]


class FakeBreaker:
    def __init__(self, sc: Scenario, delay: float) -> None:
        self.sc, self.delay = sc, delay
        self.calls: dict[str, int] = defaultdict(int)  # role -> rounds seen

    async def attack(self, spec: str, content: str, weakness_class: str, digest: LedgerDigest) -> list[dict]:
        self.calls[weakness_class] += 1
        # stagger roles so ATTACK events trickle in like a real swarm
        await asyncio.sleep(self.delay * (1 + 0.5 * list(self.sc.attacks[1]).index(weakness_class)))
        if weakness_class in self.sc.raise_on:
            raise RuntimeError("simulated provider failure")
        return self.sc.attacks.get(self.calls[weakness_class], {}).get(weakness_class, [])


class FakeVerifier:
    def __init__(self, sc: Scenario, delay: float) -> None:
        self.sc, self.delay = sc, delay

    async def verify(self, artifact: Artifact, attack: Attack) -> Verdict:
        await asyncio.sleep(self.delay / 2)
        return self.sc.oracle(self.sc.versions.index(artifact.content), attack)


def fake_agents(domain: Domain, delay: float = 0.0, scenario: Scenario | None = None, **builder_opts) -> Agents:
    sc = scenario or SCENARIOS[domain]
    verifier = FakeVerifier(sc, delay)
    return Agents(
        builder=FakeBuilder(sc, delay, **builder_opts),
        breaker=FakeBreaker(sc, delay),
        verifiers={"test": verifier, "computation": verifier, "claimCheck": verifier},
    )
