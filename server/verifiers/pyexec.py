"""PyExec v2 — ground truth for code (ANY code) and computable reasoning. Zero verdicts by LLM opinion.

Probe kinds (all fit the frozen Attack contract; no schema change):
  test{input,expected}            single call of the entry function, OR stdin->stdout for script programs
  computation{expr,expected}      code domain: an eval-expression or multi-line snippet (classes, call sequences,
                                  `forall(...)` property checks); final value in `result`
  expected sentinels              "raises ValueError" | "no_error" | "True" (property holds)
  math/reasoning computation      recompute the answer independently (enumeration etc.), or refute a claim
                                  (`# claim: <verbatim span>` first line, `expected: "True"`)

TRUST GATE: a LLM-written expectation never lands on its own when independent implementations exist.
Votes: for-attack = breaker + oracles that satisfy the expectation; for-artifact = artifact + oracles that
reproduce the artifact's behaviour. Self-evident failures (won't compile / lints) need no vote.
`landed=True` only on verified failure; malformed/disputed/infra problems never land.
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
import re
import signal
import sys
import tempfile
import weakref
from pathlib import Path

import config
from contracts import Artifact, Attack, Verdict
from verifiers.lints import run_rule
from verifiers.nli import claim_present

HARNESS = Path(__file__).with_name("_harness.py")
LINT_RE = re.compile(r"^__lint__\(\s*['\"](\w+)['\"]\s*\)$")
_SEMS: "weakref.WeakKeyDictionary" = weakref.WeakKeyDictionary()


def _sem() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    if loop not in _SEMS:
        _SEMS[loop] = asyncio.Semaphore(config.SANDBOX_CONCURRENCY)
    return _SEMS[loop]


# ---------------- entry-point / program-shape detection ----------------
def detect_entrypoint(spec: str, code: str) -> str | None:
    """Function the tests call: first top-level def named in the spec, else the LAST top-level def."""
    try:
        names = [n.name for n in ast.parse(code).body if isinstance(n, ast.FunctionDef)]
    except SyntaxError:
        return None
    for cand in re.findall(r"([A-Za-z_]\w*)\s*\(", spec):
        if cand in names:
            return cand
    return names[-1] if names else None


def is_script(code: str) -> bool:
    """stdin/stdout program: reads input() / sys.stdin or has a __main__ guard."""
    try:
        for n in ast.walk(ast.parse(code)):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "input":
                return True
            if isinstance(n, ast.Attribute) and n.attr == "stdin":
                return True
            if isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id == "__name__":
                return True
    except SyntaxError:
        pass
    return False


# ---------------- sandbox ----------------
async def run_sandbox(req: dict, timeout: float | None = None) -> dict:
    timeout = timeout or config.SANDBOX_TIMEOUT_S
    req = {**req, "mem_mb": config.SANDBOX_MEMORY_MB, "cpu_s": int(timeout) + 1}
    async with _sem():
        with tempfile.TemporaryDirectory() as tmp:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-I", str(HARNESS),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=tmp, env={"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0"}, start_new_session=True)
            try:
                out, err = await asyncio.wait_for(proc.communicate(json.dumps(req).encode()), timeout)
            except asyncio.TimeoutError:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
                await proc.wait()
                return {"status": "timeout", "actual": "TIMEOUT"}
    i = out.rfind(b"@@RESULT@@")
    if i < 0:
        return {"status": "crash", "actual": "CRASH",
                "error": err.decode(errors="replace")[-200:] or f"exit code {proc.returncode}"}
    return json.loads(out[i + 10:].split(b"\n")[0])


# ---------------- number / answer helpers ----------------
def _norm_text(s: str) -> str:
    s = (s.replace("×", "*").replace("·", "*").replace("÷", "/").replace("^", "**")
          .replace("−", "-").replace("≈", "="))
    return re.sub(r"[\s,$₹€£]", "", s)


def _to_float(s: str) -> float | None:
    s = re.sub(r"[\s,$₹€£]", "", s)
    try:
        return float(s)
    except ValueError:
        pass
    m = re.fullmatch(r"(-?\d+)/(\d+)", s)
    return int(m.group(1)) / int(m.group(2)) if m and int(m.group(2)) else None


def _claimed_values(content: str, expr: str) -> list[str]:
    """Numbers the artifact states as `<expr> = <number>`; per line, whitespace/comma/currency-insensitive."""
    pat = re.compile(re.escape(_norm_text(expr)) + r"=(-?\d+(?:\.\d+)?)(?![\d*/+\-(^]|\.\d)")
    return [m for line in content.splitlines() for m in pat.findall(_norm_text(line))]


def _matches(actual: float, claimed: str) -> bool:
    c = float(claimed)
    d = len(claimed.split(".")[1]) if "." in claimed else 0
    return abs(actual - c) <= 1e-6 * max(1, abs(actual)) or round(actual, d) == round(c, d)


def _fmt(x: float) -> str:
    return f"{x:.10g}"


def final_answer(content: str) -> str | None:
    """Last `ANSWER: ...` line of a math/reasoning artifact (the Builder prompt requires it)."""
    m = re.findall(r"(?im)^\s*[*_]*ANSWER[*_]*\s*[:=]\s*(.+?)\s*$", content)
    return m[-1] if m else None


def _norm_word(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").casefold())


def answer_matches(stated: str, r: dict) -> bool:
    """Does the artifact's stated answer equal the computed value r (an eval-mode result)?"""
    if r.get("num") is not None:
        m = re.search(r"-?\d[\d,]*(?:\.\d+)?", stated)
        return bool(m) and _matches(r["num"], m.group(0).replace(",", ""))
    return _norm_word(stated) == _norm_word(r.get("text") or r.get("actual", ""))


def values_agree(a: dict, b: dict) -> bool:
    if a.get("num") is not None and b.get("num") is not None:
        return abs(a["num"] - b["num"]) <= 1e-6 * max(1, abs(a["num"]))
    return _norm_word(a.get("text") or a.get("actual", "")) == _norm_word(b.get("text") or b.get("actual", ""))


def tally(agree: int, mirror: int, dissent: int) -> tuple[str, float]:
    """Vote rule on RAW oracle counts. The breaker is one vote FOR the attack and the artifact's author one
    vote FOR the artifact; `agree` = oracles that satisfy the attack's expectation, `mirror` = oracles that
    reproduce the artifact's behaviour, `dissent` = oracles giving a third, different answer."""
    a, m = agree + 1, mirror + 1
    if a > m:
        return "landed", 0.9 if (mirror == 0 and dissent == 0) else 0.75
    if m > a:
        return "invalid", 0.2
    if agree == 0 and dissent == 0:
        return "unverified", 0.6              # nobody could vote -> land, flagged low-confidence
    return "disputed", 0.4


def _same_failure(a: str, b: str) -> bool:
    return a == b or (a.startswith("counterexample:") and b.startswith("counterexample:"))


def _clean_output(r: dict) -> bool:
    return r["status"] == "fail" and not r.get("exc") and not str(r.get("actual", "")).startswith("raised")


class PyExecVerifier:
    """verify(artifact, attack) -> Verdict. `oracles` (OracleProvider) enables the trust gate."""

    def __init__(self, oracles=None):
        self.oracles = oracles

    async def _impls(self, art: Artifact) -> list[str]:
        if not self.oracles:
            return []
        try:
            return await self.oracles.impls(art)
        except Exception:
            return []

    async def verify(self, artifact: Artifact, attack: Attack) -> Verdict:
        if artifact.domain == "code":
            return await self._code(artifact, attack)
        if artifact.domain == "math":
            return await self._math(artifact, attack)
        raise ValueError(f"PyExec does not handle domain {artifact.domain!r}")

    # ================= code =================
    async def _code(self, art: Artifact, atk: Attack) -> Verdict:
        def mk(landed, label, actual="", ev="", conf=None):
            return Verdict(attack_id=atk.id, landed=landed, actual=actual, evidence=ev, label=label, confidence=conf)

        if atk.computation and (m := LINT_RE.match(atk.computation.expr.strip())):
            found = run_rule(m.group(1), art.content)
            return mk(bool(found), "fail" if found else "pass", "; ".join(found[:3]),
                      "static check: " + ("; ".join(found[:3]) if found else "clean"), 0.7 if found else None)

        try:
            ast.parse(art.content)
        except SyntaxError as e:
            return mk(True, "fail", "SyntaxError", f"artifact does not compile: {e.msg} (line {e.lineno})", 0.95)

        if atk.test:
            entry = detect_entrypoint(art.spec, art.content)
            base = {"input": atk.test.input, "expected": atk.test.expected}
            if entry:
                req, probe = {"kind": "test", "entry": entry, **base}, f"{entry}({atk.test.input})"
            elif is_script(art.content):
                req, probe = {"kind": "script", **base}, f"stdin {atk.test.input!r}"
            else:
                return mk(False, "invalid", "", "no function to call; use a computation snippet for classes/state")
            want = atk.test.expected
        elif atk.computation:
            req = {"kind": "snippet", "expr": atk.computation.expr, "expected": atk.computation.expected}
            probe, want = atk.computation.expr.strip().splitlines()[0][:90], atk.computation.expected
        else:
            return mk(False, "invalid", "", "code domain needs a test or computation")

        a = await run_sandbox({"mode": "probe", "code": art.content, **req})
        st = a["status"]
        if st == "pass":
            return mk(False, "pass", a.get("actual", ""), f"{probe} matched {want}")
        if st == "bad_attack":
            return mk(False, "invalid", "", f"malformed attack dropped: {a['error']}")
        if st == "syntax_error":
            return mk(True, "fail", "SyntaxError", f"artifact does not compile: {a['error']}", 0.95)
        if st == "load_error":
            return mk(True, "fail", "LoadError", f"artifact crashes on load: {a['error']}", 0.95)
        if st == "no_entry":
            return mk(True, "fail", "NoEntry", a["error"], 0.9)
        if st not in ("fail", "timeout", "crash"):
            return mk(False, "error", "", f"unhandled sandbox status {st}")
        return await self._gate(art, atk, req, a, probe, want, mk)

    async def _gate(self, art, atk, req, a, probe, want, mk) -> Verdict:
        """The artifact failed a probe. Do independent implementations back the attack?"""
        a_act = str(a.get("actual", ""))
        what = a_act + (" (deliberate raise)" if a.get("explicit") else "")
        fail_txt = f"{probe}: expected {want}, got {what}"
        codes = await self._impls(art)

        async def one(code):
            r = {"mode": "probe", **req, "code": code}
            if req["kind"] == "test":
                e = detect_entrypoint(art.spec, code)
                if not e:
                    return {"status": "abstain"}
                r["entry"] = e
            return await run_sandbox(r)

        results = await asyncio.gather(*(one(c) for c in codes)) if codes else []
        agree = mirror = dissent = 0
        for r in results:
            if r["status"] == "pass":
                agree += 1
            elif r["status"] in ("fail", "timeout", "crash"):
                if _same_failure(a_act, str(r.get("actual", ""))):
                    mirror += 1
                elif _clean_output(r):
                    dissent += 1                      # exceptions/timeouts from an oracle = abstain
        outcome, conf = tally(agree, mirror, dissent)
        n = len(results)
        lab = "timeout" if a["status"] == "timeout" else "fail"
        if a["status"] == "timeout" and outcome in ("unverified", "disputed"):
            # No independent implementation finished within the limit either: a slow or
            # overloaded sandbox, not evidence of a break. Unsettled, so it doesn't score.
            return mk(False, "indeterminate", a_act, f"{fail_txt} · no independent implementation finished in time", conf)
        if outcome == "landed":
            return mk(True, lab, a_act, f"{fail_txt} · {agree}/{n} independent implementation(s) agree with the expectation", conf)
        if outcome == "unverified":
            return mk(True, lab, a_act, fail_txt + (" · unverified: no independent implementation could vote" if not n else ""), conf)
        if outcome == "invalid":
            return mk(False, "invalid", a_act, "dropped: independent implementation(s) behave exactly like the "
                      "artifact, so the attack's expectation is probably wrong", conf)
        return mk(False, "disputed", a_act, "disputed: implementations disagree with each other; not counted", conf)

    # ================= math / computable reasoning =================
    async def _math(self, art: Artifact, atk: Attack) -> Verdict:
        def mk(landed, label, actual="", ev="", conf=None):
            return Verdict(attack_id=atk.id, landed=landed, actual=actual, evidence=ev, label=label, confidence=conf)

        if not atk.computation:
            return mk(False, "invalid", "", "math/reasoning domain needs a computation")
        expr, expected = atk.computation.expr, atk.computation.expected.strip()
        claim_span, body = None, expr
        first, _, rest = expr.partition("\n")
        if first.strip().lower().startswith("# claim:"):
            claim_span, body = first.split(":", 1)[1].strip(), rest

        r = await run_sandbox({"mode": "eval", "expr": body})
        if r["status"] != "ok":
            return mk(False, "invalid", "", f"snippet not computable: {r.get('error', r['status'])}")
        label_val = r["actual"]

        if claim_span is not None and not claim_present(claim_span, art.content):
            return mk(False, "invalid", label_val, "cited claim is not (or no longer) asserted by the answer")

        # --- refutation: a snippet that returns True = a concrete counterexample to a cited claim ---
        if expected == "True":
            if claim_span is None:
                return mk(False, "invalid", label_val, "a refutation must cite the claim with '# claim: <span>'")
            if r.get("is_true"):
                return mk(True, "fail", "True", f'counterexample verified for claim "{claim_span[:90]}"', 0.85)
            return mk(False, "pass", label_val, "snippet did not demonstrate a counterexample")

        # --- value attacks: the breaker's own number must be what the snippet really computes ---
        exp_num = _to_float(expected)
        consistent = (abs(r["num"] - exp_num) <= 1e-6 * max(1, abs(r["num"]))
                      if r.get("num") is not None and exp_num is not None
                      else _norm_word(r.get("text") or label_val) == _norm_word(expected))
        if not consistent:
            return mk(False, "invalid", label_val, f"breaker's own expected value is wrong: computed {label_val}")

        # (a) arithmetic line the answer writes as `expr = value` — deterministic, no vote needed
        if "\n" not in expr and r.get("num") is not None:
            claimed = _claimed_values(art.content, expr)
            if claimed:
                bad = [c for c in claimed if not _matches(r["num"], c)]
                if bad:
                    return mk(True, "fail", bad[0], f"answer states {expr} = {bad[0]}, computed {_fmt(r['num'])}", 1.0)
                return mk(False, "pass", _fmt(r["num"]), f"{expr} = {_fmt(r['num'])} confirmed")

        # (b) independent recomputation vs the answer's final `ANSWER:` line
        stated = final_answer(art.content)
        if stated is None:
            # The breaker's number is already proven by its own snippet; an answer that never states a
            # checkable result is the artifact's defect, not the attack's (else it scores as robust).
            return mk(True, "fail", "no ANSWER: line", f"answer never states a final 'ANSWER:' line; "
                      f"independent computation gives {label_val}", 0.8)
        if answer_matches(stated, r):
            return mk(False, "pass", label_val, f"independent computation agrees with ANSWER: {stated}")
        return await self._solver_gate(art, body, r, stated, mk)

    async def _solver_gate(self, art, body, r, stated, mk) -> Verdict:
        solvers = [s for s in await self._impls(art) if s.strip() != body.strip()]
        runs = await asyncio.gather(*(run_sandbox({"mode": "eval", "expr": s}) for s in solvers)) if solvers else []
        agree = mirror = dissent = 0
        for v in runs:
            if v["status"] != "ok":
                continue
            if values_agree(r, v):
                agree += 1
            elif answer_matches(stated, v):
                mirror += 1
            else:
                dissent += 1
        outcome, conf = tally(agree, mirror, dissent)
        msg = f"recomputed {r['actual']}, but the answer states {stated}"
        if outcome == "landed":
            return mk(True, "fail", stated, f"{msg} · {agree}/{len(runs)} independent solver(s) agree with the recomputation", conf)
        if outcome == "unverified":
            return mk(True, "fail", stated, msg + " · unverified: no independent solver could vote", conf)
        if outcome == "invalid":
            return mk(False, "invalid", stated, "dropped: an independent solver reproduces the answer's value", conf)
        return mk(False, "disputed", stated, "disputed: solvers disagree; not counted", conf)
