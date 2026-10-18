"""Build the Agents for a run. The one place that knows fake vs real.

Selection is delegated to orchestrator/seams.py, which composes real/fake per seam
(USE_REAL_BUILDER / USE_REAL_BREAKERS / USE_REAL_PYEXEC / USE_REAL_NLI; CRUCIBLE_AGENTS=real
turns everything real). The gateway is passed to seams as a factory so get_gateway()
stays the single place that constructs the shared gateway.

GATEWAY CAVEAT: the pooled, rotating gateway is still unbuilt; the only gateway is M2's
non-rotating DevGateway. Real seams run on it for local bring-up; default stays fake.
"""

from __future__ import annotations

import logging
from typing import Any

from config import Settings
from contracts import Domain
from orchestrator.agents import Agents
from orchestrator.fakes import fake_agents

log = logging.getLogger(__name__)

_GATEWAY: Any = None


def _use_fake(settings: Settings, mock: bool = False) -> bool:
    """Single fake-vs-real predicate for the gateway. Only CRUCIBLE_AGENTS=real is real;
    `mock` forces fake per run. (Per-seam switches are resolved in seams.compose.)"""
    return mock or settings.agents != "real"


def _real_gateway(settings: Settings) -> Any:
    """Process-wide gateway for real seams. DevGateway is single-key and non-rotating (see module note)."""
    global _GATEWAY
    if _GATEWAY is None:
        from orchestrator.gateway import DevGateway

        log.warning("real seam(s) using DevGateway: single-key, NO rotation/failover. "
                    "Not a production gateway — see wiring.py GATEWAY CAVEAT.")
        _GATEWAY = DevGateway()
    return _GATEWAY


def build_agents(domain: Domain, settings: Settings, mock: bool = False) -> Agents:
    if mock:
        return fake_agents(domain, delay=settings.fake_delay_sec)
    from orchestrator import seams

    return seams.compose(domain, settings, lambda: _real_gateway(settings))


def get_gateway(settings: Settings) -> Any:
    """The shared Model Gateway (exposes health()/usage when present); None unless agents == real.
    Reflects the configured mode; a per-request mock=True stream never builds a gateway (see build_agents)."""
    return None if _use_fake(settings) else _real_gateway(settings)
