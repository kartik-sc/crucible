"""Builder (author) — generate + batched patch. Qwen via Gateway role 'builder', temp 0.2.

Output is tag-delimited (<content>/<assumptions>), NOT JSON: code inside JSON strings is the #1 way
LLM output breaks.
"""
from __future__ import annotations

import re

import config
from contracts import Artifact, BuilderOutput, Domain, LandedBreak
from orchestrator.gateway import Gateway
from orchestrator.llmio import extract_tag, first_fence, strip_think

FORMAT = """Reply in EXACTLY this format and nothing else:
<content>
...your answer...
</content>
<assumptions>
- one short line per assumption you made
</assumptions>"""

SYSTEM = {
    "code": """You are the AUTHOR in an adversarial hardening loop. A swarm of red-team agents will try to break your code with executed tests, property checks, fuzzing and static analysis, and independent engineers will implement the same spec to cross-check you. Be correct, not clever.
Rules: Python 3 standard library only. Implement exactly the names/signatures the SPEC gives (functions, classes, or a stdin->stdout program). Put helper functions and classes BEFORE the main function; the function the spec names goes LAST. Handle every case the spec states or implies: empty/degenerate input, boundaries, required exceptions (raise explicitly, with a clear message), ordering and stability, and never mutate arguments or share mutable defaults. Think about invariants (what must always hold) before writing. No tests, no prose inside <content>: just code.
""" + FORMAT,
    "math": """You are the AUTHOR in an adversarial hardening loop. Independent programs will recompute every step and your final answer by exact computation and exhaustive enumeration.
Rules: restate the problem's constraints first (ranges, distinctness, ordering, edge values) and respect ALL of them. Derive step by step; write every calculation as `expression = value` in plain Python-style arithmetic (e.g. `58320 * 1.08 = 62985.6`), one per line, using * / ** and parentheses. Do not assert 'always/for all' claims you have not justified. FINISH with a line `ANSWER: <value>` containing only the final answer. Where counting or logic is involved, sanity-check small cases by hand.
""" + FORMAT,
    "factual": """You are the AUTHOR in an adversarial hardening loop. A swarm of red-team agents will check every factual claim against encyclopedic sources.
Rules: write a compact answer of short, self-contained declarative sentences, each carrying ONE checkable specific (a date, number, name or place) with the entity named explicitly (no pronouns for the subject). Only state facts you are confident about; leave out what you are unsure of instead of guessing.
""" + FORMAT,
}


def parse_builder_output(raw: str, domain: Domain) -> BuilderOutput:
    text = strip_think(raw)
    content = extract_tag(text, "content")
    assume_raw = extract_tag(text, "assumptions")
    if content is None:                                   # model ignored the format
        content = text
        if assume_raw is not None:
            content = content.split("<assumptions>")[0]
    if "</content>" in content:
        content = content.split("</content>")[0]
    if domain == "code":
        fence = first_fence(content)
        if fence is not None:
            content = fence
    assumptions = [ln.lstrip("-*• \t").strip() for ln in (assume_raw or "").splitlines()
                   if ln.strip() and ln.strip() not in ("</assumptions>",)][:8]
    return BuilderOutput(content=content.strip("\n"), assumptions=assumptions)


def looks_hardcoded(old: str, new: str, landed: list[LandedBreak]) -> bool:
    """Patch 'fixes' a test by special-casing it: the failing input AND expected literals newly appear in the code."""
    strip = lambda t: re.sub(r"\s+", "", t)
    o, n = strip(old), strip(new)
    for lb in landed:
        t = lb.attack.test
        if t:
            i, e = strip(t.input), strip(t.expected)
            if len(i) + len(e) >= 8 and i in n and e in n and not (i in o and e in o):
                return True
    return False


def describe_break(lb: LandedBreak) -> str:
    a, v = lb.attack, lb.verdict
    if a.test:
        return f"- calling the function with input `{a.test.input}` should give `{a.test.expected}`; it gave: {v.actual}"
    if a.computation:
        return f"- check `{a.computation.expr[:300]}` should give `{a.computation.expected}`; verifier: {v.evidence}"
    if a.claim_check:
        return f'- claim "{a.claim_check.claim}" is wrong; verifier: {v.evidence}'
    return f"- a prior check failed; verifier: {v.evidence}"  # defensive: validator guarantees one of the above


class Builder:
    def __init__(self, gateway: Gateway):
        self.gw = gateway

    async def _call(self, domain: Domain, user: str) -> BuilderOutput:
        res = await self.gw.call(
            "builder",
            [{"role": "system", "content": SYSTEM[domain]}, {"role": "user", "content": user + "\n/no_think"}],
            max_tokens=config.BUILDER_MAX_TOKENS, temp=config.BUILDER_TEMP, cache_prefix=SYSTEM[domain])
        return parse_builder_output(res.text, domain)

    async def generate(self, spec: str, domain: Domain) -> BuilderOutput:
        """BUILDER: (spec) -> {content, assumptions[]}"""
        user = f"SPEC:\n{spec}"
        if domain == "math":
            user += "\n\nKeep the derivation compact and FINISH with the line `ANSWER: <value>`."
        return await self._call(domain, user)

    async def patch(self, artifact: Artifact, landed: list[LandedBreak]) -> str:
        """PATCH: (artifact, landed breaks) -> content'. ONE call per round for ALL breaks.
        Returns the full patched content (str) per the M1 Builder contract (the loop uses it directly)."""
        shown = "\n".join(describe_break(lb) for lb in landed[:8])
        user = (f"SPEC:\n{artifact.spec}\n\nYOUR CURRENT ANSWER:\n{artifact.content}\n\n"
                f"VERIFIED FAILURES (ground truth, executed/checked by machines):\n{shown}\n\n"
                "Fix every failure with the smallest change that does not break anything else, and return the "
                "FULL updated answer. If a failure contradicts the SPEC itself (the check is wrong), follow the "
                "SPEC and record why in <assumptions>. Fix the GENERAL logic: never special-case the failing "
                "inputs or hard-code expected values.")
        if artifact.domain == "math":
            user += ("\n\nKeep the derivation compact (no repeated recaps) and FINISH with the line "
                     "`ANSWER: <value>`: without it the answer cannot be verified.")
        out = await self._call(artifact.domain, user)
        if artifact.domain == "code" and looks_hardcoded(artifact.content, out.content, landed):
            out = await self._call(artifact.domain, user + "\n\nYour previous attempt special-cased the failing "
                                   "inputs. Rewrite it so the underlying logic is correct for ALL inputs.")
        return out.content

    async def build_artifact(self, spec: str, domain: Domain) -> Artifact:
        out = await self.generate(spec, domain)
        return Artifact.make(domain, spec, out.content, out.assumptions, version=0)
