"""SSE events (CONTRACTS §4): one per FSM transition, small payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

EventType = Literal["STATE", "BUILDER", "ATTACK", "VERDICT", "SCORE", "ROUND_END", "DONE", "ERROR"]
State = Literal["GENERATE", "FANOUT", "VERIFY", "SCORE", "DECIDE", "PATCH", "DONE"]
DoneReason = Literal["converged", "max_rounds", "gated"]

# Guard against runaway output only: the arena renders the builder's full answer, so a
# tight cap (it was 400) cut real answers off mid-line.
PREVIEW_CHARS = 20_000


@dataclass(frozen=True)
class Event:
    type: EventType
    data: dict[str, Any]

    def sse(self) -> str:
        return f"event: {self.type}\ndata: {json.dumps(self.data, separators=(',', ':'))}\n\n"


def state(s: State, round_no: int) -> Event:
    return Event("STATE", {"state": s, "round": round_no})


def builder(version: int, content: str) -> Event:
    return Event("BUILDER", {"version": version, "contentPreview": content[:PREVIEW_CHARS]})


def attack(a: Any) -> Event:
    return Event("ATTACK", {"attack": a.to_json()})


def verdict(v: Any) -> Event:
    return Event("VERDICT", {"verdict": v.to_json()})


def score(s: Any) -> Event:
    return Event("SCORE", s.to_json())


def round_end(round_no: int, new_breaks: int) -> Event:
    return Event("ROUND_END", {"round": round_no, "newBreaks": new_breaks})


def done(reason: DoneReason, robustness: float | None, content: str | None = None) -> Event:
    """`content` is the full, uncapped hardened answer (contract ask #6)."""
    data: dict[str, Any] = {"reason": reason, "robustness": robustness}
    if content is not None:
        data["content"] = content
    return Event("DONE", data)


def error(where: str, message: str, fatal: bool) -> Event:
    return Event("ERROR", {"where": where, "message": message, "fatal": fatal})
