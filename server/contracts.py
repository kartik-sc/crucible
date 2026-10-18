"""Pydantic mirror of docs/CONTRACTS.md — the single source of truth.

Python fields are snake_case; JSON on the wire is camelCase (CONTRACTS shape).
Serialize with `model.model_dump(by_alias=True)` / `to_json()`.
"""

from __future__ import annotations

import hashlib
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

Domain = Literal["code", "factual", "math"]
WeaknessClass = Literal["boundary", "numeric_type", "spec_gap", "factual"]
WEAKNESS_CLASSES: tuple[WeaknessClass, ...] = ("boundary", "numeric_type", "spec_gap", "factual")


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    def to_json(self) -> dict:
        return self.model_dump(by_alias=True, exclude_none=True)


def spec_hash(spec: str) -> str:
    return "sha256:" + hashlib.sha256(spec.encode()).hexdigest()


# ---- Artifact ---------------------------------------------------------------

class Artifact(Model):
    domain: Domain
    spec: str
    spec_hash: str
    content: str
    assumptions: list[str] = []
    version: int = 0


# ---- Attack evidence payloads -------------------------------------------------

class TestCase(Model):
    __test__ = False  # not a pytest class
    input: str
    expected: str


class Computation(Model):
    expr: str
    expected: str


class ClaimCheck(Model):
    claim: str
    source_query: str


EvidenceKind = Literal["test", "computation", "claimCheck"]


class Attack(Model):
    # id + signature are (re)assigned by the Coordinator; breakers may omit them.
    id: str = ""
    breaker: WeaknessClass
    signature: str = ""
    rationale: str = ""
    test: Optional[TestCase] = None
    computation: Optional[Computation] = None
    claim_check: Optional[ClaimCheck] = None

    @model_validator(mode="after")
    def _exactly_one_evidence(self) -> "Attack":
        # GROUND-TRUTH RULE: no evidence, no strike.
        present = [p for p in (self.test, self.computation, self.claim_check) if p is not None]
        if len(present) != 1:
            raise ValueError(f"attack must carry exactly one evidence payload, got {len(present)}")
        return self

    @property
    def evidence_kind(self) -> EvidenceKind:
        if self.test is not None:
            return "test"
        if self.computation is not None:
            return "computation"
        return "claimCheck"


# ---- Verdict ------------------------------------------------------------------

class Verdict(Model):
    attack_id: str
    landed: bool
    actual: str = ""
    evidence: str = ""


class LandedBreak(Model):
    """What the Builder's patch call receives: the failing attack + its verdict."""
    attack: Attack
    verdict: Verdict


class LedgerDigest(Model):
    tried: list[str] = []
    survivors: list[Attack] = []
    landed: list[Attack] = []


class Score(Model):
    robustness: float
    new_breaks: int
    survived: int
    landed: int
    round: int


# ---- Agent outputs ------------------------------------------------------------

class BuildResult(Model):
    content: str
    assumptions: list[str] = []


# ---- API ----------------------------------------------------------------------

class RunRequest(Model):
    query: str
    domain: Domain
