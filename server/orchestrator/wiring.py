"""Build the Agents for a run. The one place that knows fake vs real."""

from __future__ import annotations

from typing import Any

from config import Settings
from contracts import Domain
from orchestrator.agents import Agents
from orchestrator.fakes import fake_agents


def build_agents(domain: Domain, settings: Settings, mock: bool = False) -> Agents:
    if mock or settings.agents == "fake":
        return fake_agents(domain, delay=settings.fake_delay_sec)
    # M2 seam: return Agents(builder=..., breaker=..., verifiers={"test": pyexec,
    # "computation": pyexec, "claimCheck": nli}, gateway=gateway) once those land.
    raise NotImplementedError("CRUCIBLE_AGENTS=real needs M2's builder/breaker/verifiers wired in wiring.py")


def get_gateway(settings: Settings) -> Any:
    """The shared Model Gateway (exposes health() and usage.summary()); None in fake mode."""
    # M2 seam: in real mode, return the process-wide gateway instance here.
    return None
