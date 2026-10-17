"""SSE events (CONTRACTS §4): one per FSM transition, small payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

EventType = Literal["STATE", "BUILDER", "ATTACK", "VERDICT", "SCORE", "ROUND_END", "DONE", "ERROR"]
State = Literal["GENERATE", "FANOUT", "VERIFY", "SCORE", "DECIDE", "PATCH", "DONE"]
DoneReason = Literal["converged", "max_rounds", "gated"]

PREVIEW_CHARS = 400


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


def done(reason: DoneReason, robustness: float | None) -> Event:
    return Event("DONE", {"reason": reason, "robustness": robustness})


def error(where: str, message: str, fatal: bool) -> Event:
    return Event("ERROR", {"where": where, "message": message, "fatal": fatal})
