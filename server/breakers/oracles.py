"""Independent implementations ("oracles") = N-version programming. They are written from the SPEC ONLY
(never shown the artifact) and EXECUTED, so a vote between them is machine evidence, not LLM opinion.

code domain  -> alternative implementations of the spec (brute force welcome)
math domain  -> solver programs that compute the final answer by exact computation / enumeration
Oracle failure degrades gracefully (fewer votes), it never breaks a round.
"""
from __future__ import annotations

import ast
import asyncio
import re
from typing import Protocol

import config
from contracts import Artifact
from orchestrator.gateway import Gateway
from orchestrator.llmio import extract_json
from breakers.builder import parse_builder_output

CODE_SYS = """You are an independent senior engineer. Implement the SPEC from scratch.
Priorities: (1) correct on EVERY input the spec allows, (2) the simplest, most obviously-correct approach (brute force is welcome; speed is irrelevant), (3) use exactly the function/class names and signatures the spec gives. Python 3 standard library only; no I/O unless the spec says stdin/stdout.
Reply EXACTLY:
<content>
...code only...
</content>
<assumptions>
</assumptions>"""

SOLVER_SYS = """You are a verification engineer. Write a short Python program that COMPUTES the final answer to the PROBLEM by exact computation or exhaustive enumeration (itertools, fractions, math are available). No prose reasoning, no printing: assign the final answer to a variable named `result`.
Reply EXACTLY:
<content>
...python code...
</content>
<assumptions>
</assumptions>"""

REQ_PROMPT = """Split the SPEC into at most 8 short, independently testable requirements (include the implicit ones: error behaviour, ordering, mutation, return type, constraints). Return ONLY JSON: {"requirements": ["...", "..."]}

SPEC:
"""


class OracleProvider(Protocol):
    async def impls(self, artifact: Artifact) -> list[str]: ...


class FixedOracles:
    """Pre-supplied implementations keyed by SPEC text. Tests + offline/demo fallback."""

    def __init__(self, by_spec: dict[str, list[str]]):
        self.by_spec = by_spec

    async def impls(self, artifact: Artifact) -> list[str]:
        return list(self.by_spec.get(artifact.spec, []))


def _valid(code: str, domain: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False
    if domain == "math":
        return any(isinstance(n, ast.Name) and n.id == "result" and isinstance(n.ctx, ast.Store)
                   for n in ast.walk(tree))
    return any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) for n in tree.body)


class LLMOracles:
    """Generated once per (spec, domain) and cached; concurrent callers share one generation task."""

    def __init__(self, gateway: Gateway, n: int = config.N_ORACLES):
        self.gw, self.n, self._tasks, self.errors = gateway, n, {}, 0

    async def impls(self, artifact: Artifact) -> list[str]:
        if artifact.domain == "factual":
            return []
        key = artifact.spec_hash + artifact.domain
        if key not in self._tasks:
            self._tasks[key] = asyncio.ensure_future(self._gen(artifact))
        try:
            result = await self._tasks[key]
        except Exception:
            self._tasks.pop(key, None)  # don't cache a raised generation; let the next round retry
            raise
        if not result:
            self._tasks.pop(key, None)  # empty (e.g. transient gateway outage) -> retry next round
        return list(result)

    async def _gen(self, a: Artifact) -> list[str]:
        sys_p = SOLVER_SYS if a.domain == "math" else CODE_SYS
        label = "PROBLEM" if a.domain == "math" else "SPEC"

        async def one(i: int) -> str | None:
            res = await self.gw.call("builder", [{"role": "system", "content": sys_p},
                                                 {"role": "user", "content": f"{label}:\n{a.spec}\n/no_think"}],
                                     max_tokens=config.BUILDER_MAX_TOKENS, temp=config.ORACLE_TEMP,
                                     seed=config.ORACLE_SEEDS[i % len(config.ORACLE_SEEDS)], cache_prefix=sys_p)
            code = parse_builder_output(res.text, "code").content
            return code if _valid(code, a.domain) else None

        got = await asyncio.gather(*(one(i) for i in range(self.n)), return_exceptions=True)
        self.errors += sum(isinstance(g, Exception) for g in got)
        seen, out = set(), []
        for g in got:
            if isinstance(g, str) and (k := re.sub(r"\s+", "", g)) not in seen:
                seen.add(k)
                out.append(g)
        return out


async def extract_requirements(gateway: Gateway, spec: str) -> list[str]:
    """SPEC -> R1..Rn. Lets spec_gap attack each requirement and lets M3 show requirement coverage."""
    try:
        res = await gateway.call("breaker", [{"role": "user", "content": REQ_PROMPT + spec}],
                                 max_tokens=500, temp=0.2, seed=5)
        reqs = extract_json(res.text).get("requirements", [])
        out = [str(r).strip() for r in reqs if str(r).strip()][:8]
        if out:
            return out
    except Exception:
        pass
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", spec) if len(s.strip()) > 12][:8]


def requirement_coverage(requirements: list[str], attacks) -> dict:
    """Attack rationales start with 'R#'. -> {'covered': [1,3], 'uncovered': [2], 'ratio': 0.67}"""
    hit = {int(m.group(1)) for a in attacks if (m := re.match(r"\s*R(\d+)\b", a.rationale or ""))}
    idx = set(range(1, len(requirements) + 1))
    return {"covered": sorted(hit & idx), "uncovered": sorted(idx - hit),
            "ratio": round(len(hit & idx) / len(idx), 2) if idx else 1.0}
