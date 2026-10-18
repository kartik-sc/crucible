"""Loop Engine / FSM (TR-4..TR-6).

  GENERATE -> FANOUT -> VERIFY -> SCORE -> DECIDE -> PATCH -> (next round) FANOUT ...
                                                  \\-> DONE

Every transition emits a STATE event. VERIFY re-runs the whole ledger against
the current version (new attacks + regression suite), so a patch is proven, not
assumed: fixed breaks flip to survived, broken survivors count as new breaks.

Stop (TR-5): converged when the current version fails nothing, or round == MAX_ROUNDS.
Errors (TR-6): non-fatal ones (a breaker died) stream an ERROR and continue; fatal
ones stream ERROR(fatal) and end the stream, freezing the last good version.
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from config import Settings
from contracts import Artifact, BuildResult, Domain, LandedBreak, spec_hash
from orchestrator import events as ev
from orchestrator.agents import Agents, invoke
from orchestrator.coordinator import BreakerFailed, Coordinator, FanoutStats
from orchestrator.gate import is_heavy
from orchestrator.ledger import Ledger
from verifiers.router import VerifierRouter
from verifiers.scorer import score

log = logging.getLogger(__name__)


class FatalError(Exception):
    def __init__(self, where: str, message: str) -> None:
        super().__init__(message)
        self.where = where


class CrucibleRun:
    def __init__(self, query: str, domain: Domain, agents: Agents, settings: Settings) -> None:
        self.spec = query.strip()
        self.domain = domain
        self.agents = agents
        self.settings = settings
        self.ledger = Ledger()
        self.coordinator = Coordinator(agents.breaker, settings.breaker_roles, settings.max_attacks_per_breaker)
        self.router = VerifierRouter(agents.verifiers, settings.verify_timeout_sec)
        self.artifact: Artifact | None = None  # last good version

    async def events(self) -> AsyncIterator[ev.Event]:
        try:
            async for e in self._run():
                yield e
        except FatalError as exc:
            yield ev.error(exc.where, str(exc), fatal=True)
        except asyncio.CancelledError:  # client disconnected
            raise
        except Exception as exc:  # TR-6: never crash the stream
            log.exception("crucible run crashed")
            yield ev.error("engine", f"{type(exc).__name__}: {exc}", fatal=True)

    async def _run(self) -> AsyncIterator[ev.Event]:
        yield ev.state("GENERATE", 1)
        built = await self._call("builder.generate", self.agents.builder.generate, self.spec, self.domain)
        built = built if isinstance(built, BuildResult) else BuildResult.model_validate(built)
        self.artifact = Artifact(
            domain=self.domain,
            spec=self.spec,
            spec_hash=spec_hash(self.spec),
            content=built.content,
            assumptions=built.assumptions,
            version=0,
        )
        yield ev.builder(0, built.content)

        if not is_heavy(self.domain, built.content):  # TR-3: answer once, skip the loop
            yield ev.state("DONE", 1)
            yield ev.done("gated", None, self.artifact.content)
            return

        for round_no in range(1, self.settings.max_rounds + 1):
            # ---- FANOUT
            yield ev.state("FANOUT", round_no)
            stats = FanoutStats()
            async for item in self.coordinator.fanout(
                self.spec, self.artifact.content, self.ledger, round_no, stats
            ):
                if isinstance(item, BreakerFailed):
                    yield ev.error(f"breaker:{item.role}", item.message, fatal=False)
                else:
                    yield ev.attack(item)
            if stats.failed_roles == len(self.settings.breaker_roles):
                # Silence from a dead swarm is not robustness — never report it as converged.
                raise FatalError("fanout", "every breaker failed this round")

            # ---- VERIFY (new attacks + regression suite, against the current version)
            yield ev.state("VERIFY", round_no)
            new_breaks = 0
            async for sig, was_failing, is_new, ruling in self._verify_all(round_no):
                entry = self.ledger.record(sig, ruling.verdict if ruling.settled else None)
                if entry.failing and (is_new or not was_failing):
                    new_breaks += 1
                yield ev.verdict(ruling.verdict)

            # ---- SCORE
            yield ev.state("SCORE", round_no)
            s = score(self.ledger.entries(), round_no, new_breaks)
            yield ev.score(s)

            # ---- DECIDE
            yield ev.state("DECIDE", round_no)
            failing = self.ledger.failing()
            if not failing or round_no == self.settings.max_rounds:
                yield ev.round_end(round_no, new_breaks)
                yield ev.state("DONE", round_no)
                yield ev.done(
                    "converged" if not failing else "max_rounds", s.robustness, self.artifact.content
                )
                return

            # ---- PATCH (one batched, delta-only call: failing tests + actuals only)
            yield ev.state("PATCH", round_no)
            breaks = [LandedBreak(attack=e.attack, verdict=e.verdict) for e in failing]
            content = await self._call("builder.patch", self.agents.builder.patch, self.artifact, breaks)
            self.artifact = self.artifact.model_copy(
                update={"content": str(content), "version": self.artifact.version + 1}
            )
            yield ev.builder(self.artifact.version, self.artifact.content)
            yield ev.round_end(round_no, new_breaks)

    async def _verify_all(self, round_no: int):
        """Verify every ledger entry concurrently; yield rulings as they finish."""
        artifact = self.artifact
        entries = self.ledger.entries()

        async def one(entry):
            was_failing, is_new = entry.failing, entry.round == round_no
            return entry.attack.signature, was_failing, is_new, await self.router.verify(artifact, entry.attack)

        for fut in asyncio.as_completed([one(e) for e in entries]):
            yield await fut

    async def _call(self, where: str, fn, *args):
        try:
            return await invoke(fn, *args)
        except Exception as exc:
            log.exception("%s failed", where)
            raise FatalError(where, f"{type(exc).__name__}: {exc}") from exc
