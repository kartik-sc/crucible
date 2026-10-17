"""Backend mirror of CONTRACTS.md. Wire format is camelCase (use .to_wire())."""
from __future__ import annotations

import hashlib
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

Domain = Literal["code", "factual", "math"]
WeaknessClass = Literal["boundary", "numeric_type", "spec_gap", "factual"]
ROLES: tuple[str, ...] = ("boundary", "numeric_type", "spec_gap", "factual")

# Which evidence payload each domain accepts (ground-truth rule, enforced at validation).
ALLOWED_EVIDENCE = {
    "code": {"test", "computation"},
    "math": {"computation"},
    "factual": {"claim_check"},
}


class Wire(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_wire(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


def sha(s: str, n: int = 32) -> str:
    return "sha256:" + hashlib.sha256(s.encode("utf-8")).hexdigest()[:n]


class Artifact(Wire):
    domain: Domain
    spec: str
    spec_hash: str
    content: str
    assumptions: list[str] = []
    version: int = 0

    @classmethod
    def make(cls, domain: Domain, spec: str, content: str,
             assumptions=(), version: int = 0) -> "Artifact":
        return cls(domain=domain, spec=spec, spec_hash=sha(spec, 64), content=content,
                   assumptions=list(assumptions), version=version)


class CodeTest(Wire):
    input: str
    expected: str


class Computation(Wire):
    expr: str
    expected: str


class ClaimCheck(Wire):
    claim: str
    source_query: str


class Attack(Wire):
    id: str
    breaker: WeaknessClass
    signature: str
    rationale: str = ""
    test: Optional[CodeTest] = None
    computation: Optional[Computation] = None
    claim_check: Optional[ClaimCheck] = None

    @model_validator(mode="after")
    def _exactly_one_evidence(self):
        n = sum(x is not None for x in (self.test, self.computation, self.claim_check))
        if n != 1:
            raise ValueError("GROUND-TRUTH RULE: exactly one evidence payload required")
        return self

    @property
    def kind(self) -> str:
        return "test" if self.test else "computation" if self.computation else "claim_check"


class Verdict(Wire):
    attack_id: str
    landed: bool
    actual: str = ""
    evidence: str = ""
    # PROPOSED additive fields (need A + C sign-off). Optional, so older consumers ignore them.
    label: Optional[str] = None        # pass|fail|invalid|error|timeout | SUPPORTED|CONTRADICTED|UNSUPPORTED
    confidence: Optional[float] = None


class LandedBreak(Wire):
    """What the Builder needs to patch: the probe AND the verifier's ruling."""
    attack: Attack
    verdict: Verdict


class LedgerDigest(Wire):
    tried: list[str] = []
    survivors: list[Attack] = []
    landed: list[Attack] = []


class BuilderOutput(Wire):
    content: str
    assumptions: list[str] = []
