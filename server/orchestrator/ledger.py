"""Attack Ledger: shared swarm memory (TR-9).

Append-only by signature. Each entry tracks the attack's status against the
CURRENT artifact version, so the ledger doubles as the regression suite that is
re-run after every patch.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts import Attack, LedgerDigest, Verdict


@dataclass
class Entry:
    attack: Attack
    round: int
    verdict: Verdict | None = None   # latest settled verdict, vs the current version
    settled: bool = False            # False = never verified, or last check indeterminate
    ever_landed: bool = False

    @property
    def failing(self) -> bool:
        return self.settled and self.verdict is not None and self.verdict.landed


class Ledger:
    def __init__(self) -> None:
        self._entries: dict[str, Entry] = {}

    def __contains__(self, sig: str) -> bool:
        return sig in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def add(self, attack: Attack, round: int) -> None:
        self._entries[attack.signature] = Entry(attack=attack, round=round)

    def record(self, sig: str, verdict: Verdict | None) -> Entry:
        """Store a ruling. `None` means indeterminate (timeout/error): not settled."""
        e = self._entries[sig]
        if verdict is None:
            e.settled = False
        elif e.ever_landed and not verdict.landed and verdict.label == "invalid":
            # A patch that makes a landed break uncheckable (e.g. drops the ANSWER: line)
            # has not fixed it: keep the landed ruling so the loop patches again.
            pass
        else:
            e.verdict, e.settled = verdict, True
            e.ever_landed |= verdict.landed
        return e

    def entries(self) -> list[Entry]:
        return list(self._entries.values())

    def failing(self) -> list[Entry]:
        return [e for e in self._entries.values() if e.failing]

    def digest(self) -> LedgerDigest:
        es = self._entries.values()
        return LedgerDigest(
            tried=list(self._entries),
            survivors=[e.attack for e in es if e.settled and not e.ever_landed],
            landed=[e.attack for e in es if e.ever_landed],
        )
