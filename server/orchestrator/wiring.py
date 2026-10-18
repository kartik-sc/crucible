"""Build the Agents for a run. The one place that knows fake vs real.

Selection is delegated to orchestrator/seams.py, which composes real/fake per seam
(USE_REAL_BUILDER / USE_REAL_BREAKERS / USE_REAL_PYEXEC / USE_REAL_NLI; CRUCIBLE_AGENTS=real
turns everything real). The gateway is passed to seams as a factory so a single builder
constructs the shared gateway.

GATEWAY=dev|pooled selects the gateway: `dev` is the single-key DevGateway (local bring-up),
`pooled` is the rotating ModelGateway (key pools, least-inflight, cool-downs). Both the /run
agents and get_gateway() (/health, /usage) go through the same selected instance.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from config import Settings
from contracts import Domain
from orchestrator.agents import Agents
from orchestrator.fakes import fake_agents

log = logging.getLogger(__name__)

_GATEWAY: Any = None


def _use_fake(settings: Settings, mock: bool = False) -> bool:
    """Fake-vs-real for get_gateway's /health view. Only CRUCIBLE_AGENTS=real is real;
    `mock` forces fake per run. (Per-seam real switches are resolved in seams.compose.)"""
    return mock or settings.agents != "real"


def _build_gateway() -> Any:
    """Process-wide gateway selected by GATEWAY=dev|pooled; built lazily and cached.

    Called by build_agents' factory only when a real seam is active (seams.compose), and by
    get_gateway() for /health, so the agents and the health view share one instance."""
    global _GATEWAY
    if _GATEWAY is None:
        from orchestrator.gateway import DevGateway, ModelGatewayAdapter, build_gateway

        mode = os.getenv("GATEWAY", "dev").strip().lower()
        if mode == "pooled":
            _GATEWAY = ModelGatewayAdapter(build_gateway())
        elif mode == "dev":
            _GATEWAY = DevGateway()
        else:
            raise ValueError(f"unsupported GATEWAY={mode!r}; expected dev or pooled")
        log.info("gateway selected: %s", mode)
    return _GATEWAY


def build_agents(domain: Domain, settings: Settings, mock: bool = False) -> Agents:
    if mock:
        return fake_agents(domain, delay=settings.fake_delay_sec)
    from orchestrator import seams

    return seams.compose(domain, settings, _build_gateway)


def get_gateway(settings: Settings) -> Any:
    """The shared gateway for /health and /usage; None in fake mode (no keys needed)."""
    return None if _use_fake(settings) else _build_gateway()
