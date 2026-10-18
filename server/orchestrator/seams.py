"""Per-seam real/fake composition for local bring-up on DevGateway.

Each integration seam (builder, per-role breakers, PyExec, NLI) can be turned real
independently via the USE_REAL_* switches (config.py), defaulting to fake. This lets
a single real component be exercised at a time without an all-or-nothing flip.

The fake fallbacks are sourced from one of M2's planted demo artifacts (demo/artifacts.py)
so a real builder's output is verified against a coherent, spec-matched scenario:
  - fake builder  -> the artifact's flawed content (patches to the fixed version)
  - fake breaker  -> the artifact's planted golden attack for its role (round 1)
  - fake verifier -> a conservative, not-landed placeholder (enable the real seam to judge)

This module does the agent/verifier SELECTION only. The gateway is supplied by the caller
as a factory, so get_gateway() (owned elsewhere) is never referenced here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable

import config
from contracts import Artifact, BuildResult, Domain, Verdict
from orchestrator.agents import Agents


@dataclass(frozen=True)
class _Real:
    builder: bool
    roles: frozenset
    pyexec: bool
    nli: bool

    def any(self) -> bool:
        return self.builder or bool(self.roles) or self.pyexec or self.nli


def _resolve(settings) -> _Real:
    legacy = settings.agents == "real"  # CRUCIBLE_AGENTS=real -> everything real
    roles = set(config.USE_REAL_BREAKERS)
    if legacy:
        roles |= set(settings.breaker_roles)
    return _Real(
        builder=config.USE_REAL_BUILDER or legacy,
        roles=frozenset(roles),
        pyexec=config.USE_REAL_PYEXEC or legacy,
        nli=config.USE_REAL_NLI or legacy,
    )


def active_seams(settings) -> str:
    r = _resolve(settings)
    if not r.any():
        return "none (all fake)"
    parts = []
    if r.builder:
        parts.append("builder")
    if r.roles:
        parts.append("breakers[" + ",".join(sorted(r.roles)) + "]")
    if r.pyexec:
        parts.append("pyexec")
    if r.nli:
        parts.append("nli")
    return ", ".join(parts)


def _bridge_keys() -> None:
    """DevGateway reads GROQ_API_KEY / GEMINI_API_KEY (singular); .env ships the documented
    GROQ_API_KEYS / AISTUDIO_API_KEYS pools. Seed the singular names from the first pooled key.
    Values are never logged."""
    if not os.getenv("GROQ_API_KEY"):
        pool = [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()]
        if pool:
            os.environ["GROQ_API_KEY"] = pool[0]
    if not os.getenv("GEMINI_API_KEY"):
        pool = [k.strip() for k in os.getenv("AISTUDIO_API_KEYS", "").split(",") if k.strip()]
        if pool:
            os.environ["GEMINI_API_KEY"] = pool[0]


def _demo_artifact(domain: Domain):
    import demo.artifacts as D

    key = config.DEMO_ARTIFACT
    if key and key in D.ALL:
        return D.ALL[key]
    for d in D.ALL.values():
        if d.domain == domain:
            return d
    raise RuntimeError(f"no demo artifact for domain {domain!r} (set DEMO_ARTIFACT)")


class _DemoFakeBuilder:
    def __init__(self, demo) -> None:
        self.demo = demo

    async def generate(self, spec: str, domain: Domain) -> BuildResult:
        return BuildResult(content=self.demo.flawed, assumptions=list(self.demo.assumptions))

    async def patch(self, artifact: Artifact, breaks) -> str:
        return self.demo.fixed


class _SeededRealBuilder:
    """generate() serves the planted flawed content (guarantees a flaw to land); patch() is the real
    builder, so the patch is a genuine model call from the landed verdict. For USE_REAL_BUILDER=1 + SEED_FLAWED=1."""

    def __init__(self, demo, real_builder) -> None:
        self.demo = demo
        self.real = real_builder

    async def generate(self, spec: str, domain: Domain) -> BuildResult:
        return BuildResult(content=self.demo.flawed, assumptions=list(self.demo.assumptions))

    async def patch(self, artifact: Artifact, breaks):
        return await self.real.patch(artifact, breaks)


class _DemoFakeBreaker:
    """Emits the planted golden attack for its role, once (round 1). Coordinator assigns id/sig."""

    def __init__(self, demo) -> None:
        self.demo = demo
        self._fired: set[str] = set()

    async def attack(self, spec: str, content: str, weakness_class: str, digest) -> list:
        g = self.demo.golden
        if g.breaker == weakness_class and weakness_class not in self._fired:
            self._fired.add(weakness_class)
            return [g.to_json()]
        return []


class _ScriptedVerifier:
    """Fallback when a verifier seam is still fake: conservative, never lands (can't judge real output)."""

    async def verify(self, artifact: Artifact, attack) -> Verdict:
        return Verdict(attack_id=attack.id, landed=False, label="pass",
                       evidence="(scripted fallback: verifier seam is fake — enable USE_REAL_PYEXEC/USE_REAL_NLI)")


class _DemoThenLLMOracles:
    """Planted oracles for the demo spec; generated ones for any other query. Without
    oracles every artifact failure lands 'unverified', so a wrong attack counts as a break."""

    def __init__(self, fixed: Any, llm: Any) -> None:
        self.fixed, self.llm = fixed, llm

    async def impls(self, artifact: Artifact) -> list[str]:
        got = await self.fixed.impls(artifact) if self.fixed else []
        return got or (await self.llm.impls(artifact) if self.llm else [])


class _MixedBreaker:
    """Real M2 breaker for roles in `roles`; the demo fallback for the rest."""

    def __init__(self, domain: Domain, gateway: Any, roles: frozenset, fallback: _DemoFakeBreaker) -> None:
        from breakers.breakers import make_swarm

        self.domain = domain
        self.fallback = fallback
        self.real = {b.role: b for b in make_swarm(gateway) if b.role in roles}

    async def attack(self, spec: str, content: str, weakness_class: str, digest) -> list:
        breaker = self.real.get(weakness_class)
        if breaker is None:
            return await self.fallback.attack(spec, content, weakness_class, digest)
        return await breaker.attack(Artifact.make(self.domain, spec, content), digest)


def compose(domain: Domain, settings, gateway_factory: Callable[[], Any]) -> Agents:
    real = _resolve(settings)
    if not real.any():
        from orchestrator.fakes import fake_agents

        return fake_agents(domain, delay=settings.fake_delay_sec)

    demo = _demo_artifact(domain)
    gateway = None
    if real.builder or real.roles:
        _bridge_keys()
        gateway = gateway_factory()

    if real.builder:
        from breakers.builder import Builder

        real_builder = Builder(gateway)
        builder: Any = _SeededRealBuilder(demo, real_builder) if config.SEED_FLAWED else real_builder
    else:
        builder = _DemoFakeBuilder(demo)

    fallback_breaker = _DemoFakeBreaker(demo)
    breaker: Any = _MixedBreaker(domain, gateway, real.roles, fallback_breaker) if real.roles else fallback_breaker

    if real.pyexec:
        from breakers.oracles import FixedOracles, LLMOracles
        from verifiers.pyexec import PyExecVerifier

        fixed = FixedOracles({demo.spec: demo.oracles}) if demo.oracles else None
        llm = LLMOracles(gateway) if gateway is not None else None
        oracles = _DemoThenLLMOracles(fixed, llm) if (fixed or llm) else None
        code_verifier: Any = PyExecVerifier(oracles=oracles)
    else:
        code_verifier = _ScriptedVerifier()

    if real.nli:
        from verifiers.nli import NLIVerifier

        claim_verifier: Any = NLIVerifier()
    else:
        claim_verifier = _ScriptedVerifier()

    return Agents(
        builder=builder,
        breaker=breaker,
        verifiers={"test": code_verifier, "computation": code_verifier, "claimCheck": claim_verifier},
        gateway=gateway,
    )
