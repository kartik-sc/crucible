"""Breaker swarm scaffold. One class, four roles (prompt + temp + seed), Gemma via Gateway role 'breaker'.

Pipeline: ledger-aware prompt -> model call -> parse JSON -> validate (ground-truth rule + domain
evidence) -> ONE terse repair retry if nothing usable parsed -> drop. No repair loops.
Gateway errors PROPAGATE (M1 fans out with gather(return_exceptions=True) and emits ERROR events).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..orchestrator import config
from ..orchestrator.contracts import ALLOWED_EVIDENCE, ROLES, Artifact, Attack, LedgerDigest, sha
from ..orchestrator.gateway import Gateway
from ..orchestrator.llmio import extract_json
from ..orchestrator.signatures import compute_signature
from ..breakers.prompts import EVIDENCE, build_prompt


@dataclass
class BreakerStats:
    calls: int = 0
    parsed_first_try: int = 0
    repaired: int = 0
    failed: int = 0            # nothing usable even after repair
    attacks_kept: int = 0
    attacks_dropped: int = 0   # schema/evidence/domain invalid
    attacks_duplicate: int = 0

    @property
    def hit_rate(self) -> float:
        """Share of calls that produced usable output WITHOUT repair (day-0 metric)."""
        return self.parsed_first_try / self.calls if self.calls else 0.0


def _s(v) -> str:
    return v.strip() if isinstance(v, str) else repr(v)


def build_attack(item: dict, domain: str, role: str) -> Attack:
    if not isinstance(item, dict):
        raise ValueError("attack is not an object")
    ev = {}
    for src, dst in (("test", "test"), ("computation", "computation"),
                     ("claimCheck", "claim_check"), ("claim_check", "claim_check")):
        if item.get(src):
            if not isinstance(item[src], dict):
                raise ValueError("evidence must be an object")
            ev[dst] = {k: _s(v) for k, v in item[src].items()}
    atk = Attack(id="pending", breaker=role, signature="pending",
                 rationale=str(item.get("rationale", ""))[:200], **ev)
    if atk.kind not in ALLOWED_EVIDENCE[domain]:
        raise ValueError(f"{atk.kind} evidence not allowed in domain {domain}")
    for need in ({"test": [atk.test and atk.test.expected],
                  "computation": [atk.computation and atk.computation.expr, atk.computation and atk.computation.expected],
                  "claim_check": [atk.claim_check and atk.claim_check.claim,
                                  atk.claim_check and atk.claim_check.source_query]}[atk.kind]):
        if not need:
            raise ValueError("empty evidence field")
    sig = compute_signature(domain, atk)
    atk.signature, atk.id = sig, "atk_" + sha(sig + role, 8)[-8:]
    return atk


def finalize(domain: str, role: str, rationale: str, **ev) -> Attack:
    """Build a validated Attack with signature + id (used by the deterministic auditors)."""
    atk = Attack(id="pending", breaker=role, signature="pending", rationale=rationale[:200], **ev)
    sig = compute_signature(domain, atk)
    atk.signature, atk.id = sig, "atk_" + sha(sig + role, 8)[-8:]
    return atk


def parse_attacks(raw: str, domain: str, role: str) -> tuple[list[Attack], int]:
    """-> (valid attacks, dropped count). Raises ValueError if no JSON attack list can be found."""
    obj = extract_json(raw)
    items = obj.get("attacks") if isinstance(obj, dict) else obj
    if not isinstance(items, list):
        raise ValueError("no 'attacks' list")
    good, dropped = [], 0
    for it in items:
        try:
            good.append(build_attack(it, domain, role))
        except (ValueError, TypeError):
            dropped += 1
    return good, dropped


class Breaker:
    def __init__(self, role: str, gateway: Gateway, *, max_attacks: int = config.MAX_ATTACKS_PER_BREAKER,
                 temp: float | None = None, seed: int | None = None,
                 requirements: list[str] | None = None):
        assert role in ROLES, role
        self.role, self.gw, self.max_attacks = role, gateway, max_attacks
        self.requirements = requirements or []      # R1..Rn from extract_requirements(); optional
        self.temp = config.BREAKER_TEMPS[role] if temp is None else temp
        self.seed = config.BREAKER_SEEDS[role] if seed is None else seed
        self.stats = BreakerStats()

    async def attack(self, artifact: Artifact, ledger: LedgerDigest | None = None) -> list[Attack]:
        """BREAKER: (artifact, ledgerDigest) -> Attack[]  (<= max_attacks, novel only, evidence required)."""
        self.stats.calls += 1
        prompt = build_prompt(self.role, artifact, ledger, self.max_attacks, self.requirements)
        res = await self.gw.call(self.role_name, [{"role": "user", "content": prompt}],
                                 max_tokens=config.BREAKER_MAX_TOKENS, temp=self.temp, seed=self.seed,
                                 cache_prefix=prompt.split("=== SPEC ===")[0])
        attacks, dropped, ok = self._try(res.text, artifact.domain)
        if ok and attacks:
            self.stats.parsed_first_try += 1
        elif not attacks and (not ok or dropped):          # unparseable OR everything invalid -> one retry
            repair = await self.gw.call(
                self.role_name,
                [{"role": "user", "content":
                  "Your previous output was not usable. Return ONLY a JSON object of this shape, nothing else.\n"
                  f"{EVIDENCE[artifact.domain]}\n\nPrevious output:\n{res.text[:1500]}\n\nJSON:"}],
                max_tokens=config.REPAIR_MAX_TOKENS, temp=0.0, seed=self.seed)
            attacks, dropped2, ok = self._try(repair.text, artifact.domain)
            dropped += dropped2
            if attacks:
                self.stats.repaired += 1
            else:
                self.stats.failed += 1
        elif ok:
            self.stats.parsed_first_try += 1               # valid JSON, genuinely nothing to report
        self.stats.attacks_dropped += dropped
        return self._novel(attacks, ledger)

    role_name = "breaker"       # Gateway role key (all four agents share the Gemma endpoint)

    def _try(self, text: str, domain: str):
        try:
            a, d = parse_attacks(text, domain, self.role)
            return a, d, True
        except ValueError:
            return [], 0, False

    def _novel(self, attacks: list[Attack], ledger: LedgerDigest | None) -> list[Attack]:
        seen = set(ledger.tried) if ledger else set()
        out = []
        for a in attacks:
            if a.signature in seen:
                self.stats.attacks_duplicate += 1
                continue
            seen.add(a.signature)
            out.append(a)
        out = out[: self.max_attacks]
        self.stats.attacks_kept += len(out)
        return out


def make_swarm(gateway: Gateway, **kw) -> list[Breaker]:
    """The four breakers, fixed order: boundary, numeric_type, spec_gap, factual."""
    return [Breaker(r, gateway, **kw) for r in ROLES]
