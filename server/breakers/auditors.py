"""Zero-LLM breakers. Same interface as Breaker (`await b.attack(artifact, ledger) -> Attack[]`), so M1 just
adds them to the fan-out. No tokens, no network: they find bugs the LLM breakers can't be trusted to guess.

  LintBreaker         static rules (mutable defaults, undefined names, swallowed errors, ...)   code
  FuzzBreaker         differential fuzzing: artifact vs independent implementations, shrunk       code
  EquationBreaker     audits EVERY `expr = value` line in the answer                              math
  AnswerAuditBreaker  independent solver programs vs the final `ANSWER:` line                     math
Their attacks still go through the normal verifier (re-checked, voted), so nothing lands by assertion.
"""
from __future__ import annotations

import ast
import asyncio
import re

from ..orchestrator import config
from ..orchestrator.contracts import Artifact, Attack, LedgerDigest
from ..verifiers.lints import RULE_CLASS, all_findings
from ..verifiers.pyexec import (_fmt, _matches, answer_matches, detect_entrypoint, final_answer,
                             run_sandbox, values_agree)
from ..breakers.breakers import finalize


class Auditor:
    role = "boundary"
    name = "auditor"

    async def attack(self, artifact: Artifact, ledger: LedgerDigest | None = None) -> list[Attack]:
        seen = set(ledger.tried) if ledger else set()
        out = []
        for a in await self._find(artifact):
            if a.signature not in seen:
                seen.add(a.signature)
                out.append(a)
        return out[: config.MAX_ATTACKS_PER_BREAKER]

    async def _find(self, art: Artifact) -> list[Attack]:
        raise NotImplementedError


class LintBreaker(Auditor):
    name = "lint"

    async def _find(self, art):
        if art.domain != "code":
            return []
        from ..orchestrator.contracts import Computation
        return [finalize("code", RULE_CLASS[rule], f"static: {found[0]}",
                         computation=Computation(expr=f"__lint__('{rule}')", expected="[]"))
                for rule, found in all_findings(art.content).items()]


class FuzzBreaker(Auditor):
    """Differential fuzz. Needs >=2 independent implementations to out-vote the artifact (or 1 to detect
    crashes/hangs). Emits the SHRUNK failing input with the oracles' majority output as the expectation."""
    name = "fuzz"
    role = "boundary"

    def __init__(self, oracles):
        self.oracles = oracles

    async def _find(self, art):
        if art.domain != "code" or not self.oracles:
            return []
        try:
            codes = await self.oracles.impls(art)
        except Exception:
            return []
        entry = detect_entrypoint(art.spec, art.content)
        if not entry or not codes:
            return []
        from ..orchestrator.contracts import CodeTest
        r = await run_sandbox({"mode": "diff", "codes": [art.content, *codes], "budget": config.FUZZ_TIMEOUT_S - 1,
                               "entries": [entry, *[detect_entrypoint(art.spec, c) for c in codes]],
                               "n": config.FUZZ_SAMPLES}, timeout=config.FUZZ_TIMEOUT_S)
        if r.get("status") != "found":
            return []
        return [finalize("code", "boundary", f"fuzz: {entry}({r['input']}) disagrees with independent implementations",
                         test=CodeTest(input=r["input"], expected=r["expected"]))]


_ARITH_RUN = re.compile(r"[\d.,()+\-*/^×÷·−\s]+$")
_RHS = re.compile(r"\s*(-?\d[\d,]*(?:\.\d+)?)(?![\d*/+\-^(]|\.\d)")


def safe_arith(expr: str) -> float | None:
    """Evaluate plain arithmetic WITHOUT exec: numbers, + - * / // % **, unary, parentheses."""
    e = expr.replace("×", "*").replace("·", "*").replace("÷", "/").replace("^", "**").replace("−", "-")
    e = re.sub(r"(?<=\d),(?=\d{3}\b)", "", e)
    try:
        t = ast.parse(e.strip(), mode="eval")
    except SyntaxError:
        return None

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -ev(n.operand) if isinstance(n.op, ast.USub) else ev(n.operand)
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            op = type(n.op)
            if op is ast.Pow:
                if abs(b) > 100 or abs(a) > 1e9:
                    raise ValueError
                return a ** b
            return {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                    ast.Div: lambda: a / b, ast.FloorDiv: lambda: a // b, ast.Mod: lambda: a % b}[op]()
        raise ValueError

    try:
        return float(ev(t))
    except Exception:
        return None


def equations(content: str) -> list[tuple[str, str]]:
    """(lhs_text, claimed_rhs) for every `<arithmetic> = <number>` in the answer, chained equals included."""
    out = []
    for line in content.splitlines():
        for m in re.finditer(r"(?<![=<>!])=(?!=)", line):
            lm = _ARITH_RUN.search(line[:m.start()])
            rm = _RHS.match(line[m.end():])
            if not lm or not rm:
                continue
            toks = lm.group(0).strip().strip(",").split()
            for i in range(len(toks)):
                cand = " ".join(toks[i:])
                if re.search(r"[+\-*/^×÷·−]", cand[1:] or "") and safe_arith(cand) is not None:
                    out.append((cand, rm.group(1).replace(",", "")))
                    break
    return out


class EquationBreaker(Auditor):
    """Audits every arithmetic line; no breaker has to happen to pick the wrong one."""
    name = "equations"
    role = "numeric_type"

    async def _find(self, art):
        if art.domain != "math":
            return []
        from ..orchestrator.contracts import Computation
        out = []
        for lhs, claimed in equations(art.content):
            val = safe_arith(lhs)
            if val is not None and not _matches(val, claimed):
                out.append(finalize("math", "numeric_type", f"{lhs} = {_fmt(val)}, answer says {claimed}",
                                    computation=Computation(expr=lhs, expected=_fmt(val))))
        return out


class AnswerAuditBreaker(Auditor):
    """Independent solver programs vs the answer's final `ANSWER:` line. Emits an attack only when >=2
    solvers agree with each other and disagree with the answer."""
    name = "answer_audit"
    role = "spec_gap"

    def __init__(self, oracles):
        self.oracles = oracles

    async def _find(self, art):
        if art.domain != "math" or not self.oracles:
            return []
        stated = final_answer(art.content)
        try:
            solvers = await self.oracles.impls(art)
        except Exception:
            return []
        if stated is None or len(solvers) < 2:
            return []
        runs = await asyncio.gather(*(run_sandbox({"mode": "eval", "expr": s}) for s in solvers))
        ok = [(s, r) for s, r in zip(solvers, runs) if r["status"] == "ok"]
        from ..orchestrator.contracts import Computation
        for i, (code, r) in enumerate(ok):
            peers = [r2 for j, (_, r2) in enumerate(ok) if j != i and values_agree(r, r2)]
            if peers and not answer_matches(stated, r):
                return [finalize("math", "spec_gap", f"independent solvers compute {r['actual']}; answer states {stated}",
                                 computation=Computation(expr=code, expected=r["actual"]))]
        return []


def make_auditors(domain: str, oracles=None) -> list[Auditor]:
    """Deterministic breakers for a domain. Add them to the same fan-out as the four LLM breakers."""
    if domain == "code":
        return [LintBreaker(), FuzzBreaker(oracles)]
    if domain == "math":
        return [EquationBreaker(), AnswerAuditBreaker(oracles)]
    return []
