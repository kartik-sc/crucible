"""Pre-staged PLANTED-FLAW artifacts for the 2-minute demo (code x2, math, reasoning, factual).

Each has: a confident-looking flawed answer (most probes pass = green, one real break = red),
the golden attack that exposes it, and a fixed version (what the patch should converge to).
Used by tests, the smoke script, and as the backup-video / offline fallback.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..orchestrator.contracts import Artifact, Attack, ClaimCheck, CodeTest, Computation, Domain
from ..orchestrator.signatures import compute_signature


@dataclass
class DemoArtifact:
    key: str
    domain: Domain
    spec: str
    flawed: str
    fixed: str
    assumptions: list[str]
    golden: Attack
    flaw_note: str
    fixtures: dict[str, list[str]]       # offline retrieval passages (factual only)
    oracles: list[str] = field(default_factory=list)   # independent implementations / solver programs (offline)

    def artifact(self, fixed: bool = False, version: int = 0) -> Artifact:
        return Artifact.make(self.domain, self.spec, self.fixed if fixed else self.flawed,
                             self.assumptions, version)


def _golden(domain: Domain, breaker: str, **ev) -> Attack:
    a = Attack(id="pending", breaker=breaker, signature="pending", rationale="planted flaw", **ev)
    a.signature = compute_signature(domain, a)
    a.id = "atk_golden_" + domain
    return a


# ---------------- CODE ----------------
_CODE_SPEC = ("Implement merge_intervals(intervals): given a list of [start, end] pairs (start <= end), return the "
              "minimal sorted list of non-overlapping intervals covering the same points. Intervals that touch at "
              "an endpoint (e.g. [1,2] and [2,3]) count as overlapping and MUST be merged. Empty input returns []. "
              "Must not mutate the input.")
_CODE_FLAWED = '''def merge_intervals(intervals):
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda p: p[0])
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        last = merged[-1]
        if start < last[1]:
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return merged
'''
CODE = DemoArtifact(
    key="code", domain="code", spec=_CODE_SPEC, flawed=_CODE_FLAWED,
    fixed=_CODE_FLAWED.replace("if start < last[1]:", "if start <= last[1]:"),
    assumptions=["each interval has exactly two numbers", "start <= end"],
    golden=_golden("code", "boundary", test=CodeTest(input="[[1,2],[2,3]]", expected="[[1, 3]]")),
    flaw_note="`<` instead of `<=`: touching intervals are not merged.", fixtures={},
    oracles=[
        "def merge_intervals(intervals):\n    out = []\n    for s, e in sorted(intervals):\n"
        "        if out and s <= out[-1][1]:\n            out[-1][1] = max(out[-1][1], e)\n"
        "        else:\n            out.append([s, e])\n    return out\n",
        "def merge_intervals(intervals):\n    items = [list(x) for x in intervals]\n    changed = True\n"
        "    while changed:\n        changed = False\n        for i in range(len(items)):\n"
        "            for j in range(i + 1, len(items)):\n                a, b = items[i], items[j]\n"
        "                if a[0] <= b[1] and b[0] <= a[1]:\n"
        "                    items[i] = [min(a[0], b[0]), max(a[1], b[1])]\n                    del items[j]\n"
        "                    changed = True\n                    break\n            if changed:\n                break\n"
        "    return sorted(items)\n"])

# ---------------- MATH ----------------
_MATH_SPEC = "Compute the amount after 3 years on Rs 50,000 invested at 8% p.a. compounded annually, and the interest earned."
_MATH_FLAWED = """Annual growth factor = 1 + 8/100 = 1.08.
Year 1: 50000 * 1.08 = 54000
Year 2: 54000 * 1.08 = 58320
Year 3: 58320 * 1.08 = 62895.6
Final amount = Rs 62895.60
Interest earned = 62895.6 - 50000 = 12895.6
ANSWER: 62895.6
"""
MATH = DemoArtifact(
    key="math", domain="math", spec=_MATH_SPEC, flawed=_MATH_FLAWED,
    fixed=_MATH_FLAWED.replace("62895.6", "62985.6").replace("62895.60", "62985.60").replace("12895.6", "12985.6"),
    assumptions=["interest compounds once per year", "no taxes or fees"],
    golden=_golden("math", "boundary", computation=Computation(expr="58320 * 1.08", expected="62985.6")),
    flaw_note="Transposed digits in Year 3 (62895.6 vs 62985.6) that then propagate to the final answer.",
    fixtures={})

# ---------------- FACTUAL ----------------
_FACT_SPEC = "Give the key facts about the James Webb Space Telescope: who built it, its launch, mirror, and orbit."
_FACT_FLAWED = ("The James Webb Space Telescope (JWST) is a space observatory built by NASA with ESA and CSA. "
                "JWST launched on 25 December 2022 aboard an Ariane 5 rocket from Kourou, French Guiana. "
                "Its primary mirror is 6.5 metres across and is made of 18 gold-coated beryllium hexagonal segments. "
                "JWST operates near the Sun-Earth L2 point, about 1.5 million kilometres from Earth.")
FACT = DemoArtifact(
    key="factual", domain="factual", spec=_FACT_SPEC, flawed=_FACT_FLAWED,
    fixed=_FACT_FLAWED.replace("25 December 2022", "25 December 2021"),
    assumptions=["facts as of the published mission record"],
    golden=_golden("factual", "boundary", claim_check=ClaimCheck(
        claim="JWST launched on 25 December 2022 aboard an Ariane 5 rocket from Kourou, French Guiana",
        source_query="James Webb Space Telescope launch")),
    flaw_note="Launch year is 2021, not 2022.",
    fixtures={"james webb": [
        "The James Webb Space Telescope (JWST) was launched on 25 December 2021 on an Ariane 5 rocket from Kourou, French Guiana.",
        "JWST's primary mirror is 6.5 metres across and consists of 18 hexagonal gold-coated beryllium segments."]})

# ---------------- CODE (class / stateful) ----------------
_LRU_SPEC = ("Implement class LRUCache(capacity) with get(key) -> value or -1 if absent (and mark the key as most "
             "recently used) and put(key, value) (insert/update, mark most recently used; when size exceeds capacity "
             "evict the least recently used key).")
_LRU_FLAWED = '''class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.data = {}
        self.order = []

    def get(self, key):
        if key not in self.data:
            return -1
        return self.data[key]

    def put(self, key, value):
        if key in self.data:
            self.order.remove(key)
        elif len(self.data) >= self.capacity:
            oldest = self.order.pop(0)
            del self.data[oldest]
        self.data[key] = value
        self.order.append(key)
'''
LRU = DemoArtifact(
    key="lru", domain="code", spec=_LRU_SPEC, flawed=_LRU_FLAWED,
    fixed=_LRU_FLAWED.replace("        return self.data[key]\n",
                              "        self.order.remove(key)\n        self.order.append(key)\n        return self.data[key]\n"),
    assumptions=["capacity >= 1", "keys are hashable"],
    golden=_golden("code", "spec_gap", computation=Computation(
        expr="c = LRUCache(2)\nc.put(1, 1)\nc.put(2, 2)\nc.get(1)\nc.put(3, 3)\nresult = c.get(2)", expected="-1")),
    flaw_note="get() does not refresh recency, so the wrong key is evicted.", fixtures={},
    oracles=[
        "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, capacity):\n"
        "        self.c, self.d = capacity, OrderedDict()\n    def get(self, key):\n        if key not in self.d:\n"
        "            return -1\n        self.d.move_to_end(key)\n        return self.d[key]\n"
        "    def put(self, key, value):\n        self.d[key] = value\n        self.d.move_to_end(key)\n"
        "        if len(self.d) > self.c:\n            self.d.popitem(last=False)\n",
        "class LRUCache:\n    def __init__(self, capacity):\n        self.cap, self.items = capacity, []\n"
        "    def get(self, key):\n        for i, (k, v) in enumerate(self.items):\n            if k == key:\n"
        "                self.items.append(self.items.pop(i))\n                return v\n        return -1\n"
        "    def put(self, key, value):\n        for i, (k, v) in enumerate(self.items):\n            if k == key:\n"
        "                self.items.pop(i)\n                break\n        self.items.append((key, value))\n"
        "        if len(self.items) > self.cap:\n            self.items.pop(0)\n"])

# ---------------- REASONING (counting; the arithmetic is right, the logic is wrong) ----------------
_REASON_SPEC = "How many 4-digit positive integers (1000 to 9999) have digits that sum to 10?"
_REASON_FLAWED = """Write the number as abcd with a in 1..9 and b, c, d in 0..9, and a + b + c + d = 10.
Let a' = a - 1, so a' + b + c + d = 9 with all variables >= 0.
By stars and bars the number of solutions is C(9 + 3, 3) = 220.
Every such solution is a valid 4-digit number.
ANSWER: 220
"""
REASON = DemoArtifact(
    key="reasoning", domain="math", spec=_REASON_SPEC, flawed=_REASON_FLAWED,
    fixed=_REASON_FLAWED.replace("Every such solution is a valid 4-digit number.",
                                 "One solution (a' = 9, i.e. a = 10) is invalid, so subtract 1: 220 - 1 = 219.")
                        .replace("ANSWER: 220", "ANSWER: 219"),
    assumptions=["4-digit means 1000..9999"],
    golden=_golden("math", "spec_gap", computation=Computation(
        expr="sum(1 for n in range(1000, 10000) if sum(map(int, str(n))) == 10)", expected="219")),
    flaw_note="Stars-and-bars ignores the digit cap a <= 9: the arithmetic is correct, the model is wrong.",
    fixtures={},
    oracles=["result = sum(1 for n in range(1000, 10000) if sum(map(int, str(n))) == 10)",
             "count = 0\nfor a in range(1, 10):\n    for b in range(10):\n        for c in range(10):\n"
             "            d = 10 - a - b - c\n            if 0 <= d <= 9:\n                count += 1\nresult = count"])

ALL = {"code": CODE, "lru": LRU, "math": MATH, "reasoning": REASON, "factual": FACT}


def all_demos() -> list[DemoArtifact]:
    return list(ALL.values())


def demo_oracles():
    """FixedOracles over every demo spec — deterministic offline stand-in for LLMOracles."""
    from ..breakers.oracles import FixedOracles
    return FixedOracles({d.spec: d.oracles for d in ALL.values() if d.oracles})
