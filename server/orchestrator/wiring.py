"""Build the Agents for a run. The one place that knows fake vs real.

Real mode wires M2's agents behind the M1 contracts (orchestrator/agents.py):
  builder   -> M2 Builder (generate / patch)
  breaker   -> _BreakerScaffold: adapts M2's four per-role breakers + the deterministic
               auditors to M1's single breaker.attack(spec, content, weakness_class, digest)
  verifiers -> {"test": PyExec, "computation": PyExec, "claimCheck": NLI}

GATEWAY CAVEAT: the pooled, rotating Model Gateway described in .env.example/EXECUTION.md
was never built (M1 owned it; get_gateway returned None). The only gateway in the repo is
M2's DevGateway — a single-key, NON-ROTATING dev client its own docstring says not to ship
into /run. Real mode uses it with a warning so the system can run end-to-end on one key, but
production rotation/failover is an open decision (see PR notes). Default stays fake.
"""

from __future__ import annotations

import logging
from typing import Any

from config import Settings
from contracts import Artifact, Domain
from orchestrator.agents import Agents
from orchestrator.fakes import fake_agents

log = logging.getLogger(__name__)

_GATEWAY: Any = None


def _real_gateway(settings: Settings) -> Any:
    """Process-wide gateway for real mode. DevGateway is single-key and non-rotating (see module note)."""
    global _GATEWAY
    if _GATEWAY is None:
        from orchestrator.gateway import DevGateway

        log.warning("CRUCIBLE_AGENTS=real using DevGateway: single-key, NO rotation/failover. "
                    "Not a production gateway — see wiring.py GATEWAY CAVEAT.")
        _GATEWAY = DevGateway()
    return _GATEWAY


class _BreakerScaffold:
    """Adapts M2's per-role breakers (+ deterministic auditors) to M1's single Breaker protocol.

    M1's Coordinator calls attack(spec, content, weakness_class, digest) once per role and then
    validates, assigns id/signature and dedups. We rebuild the Artifact (domain is fixed per run),
    run the matching LLM breaker plus any auditor that owns this role, and return raw attacks.
    """

    def __init__(self, domain: Domain, gateway: Any, oracles: Any) -> None:
        from breakers.auditors import make_auditors
        from breakers.breakers import make_swarm

        self.domain = domain
        self.swarm = {b.role: b for b in make_swarm(gateway)}
        self.auditors = make_auditors(domain, oracles)

    async def attack(self, spec: str, content: str, weakness_class: str, digest: Any) -> list:
        artifact = Artifact.make(self.domain, spec, content)
        attacks: list = []
        breaker = self.swarm.get(weakness_class)
        if breaker is not None:
            attacks += await breaker.attack(artifact, digest)
        for auditor in self.auditors:
            if auditor.role == weakness_class:
                attacks += await auditor.attack(artifact, digest)
        return attacks


def build_agents(domain: Domain, settings: Settings, mock: bool = False) -> Agents:
    if mock or settings.agents == "fake":
        return fake_agents(domain, delay=settings.fake_delay_sec)

    from breakers.builder import Builder
    from breakers.oracles import LLMOracles
    from verifiers.nli import NLIVerifier
    from verifiers.pyexec import PyExecVerifier

    gateway = _real_gateway(settings)
    oracles = LLMOracles(gateway)
    pyexec = PyExecVerifier(oracles=oracles)
    nli = NLIVerifier()
    return Agents(
        builder=Builder(gateway),
        breaker=_BreakerScaffold(domain, gateway, oracles),
        verifiers={"test": pyexec, "computation": pyexec, "claimCheck": nli},
        gateway=gateway,
    )


def get_gateway(settings: Settings) -> Any:
    """The shared Model Gateway (exposes health()/usage when present); None in fake mode."""
    if settings.agents == "fake":
        return None
    return _real_gateway(settings)
