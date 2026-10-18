"""Breaker prompts v2 — general code + computable reasoning.
Static prefix first (cacheable) -> role/domain focus -> dynamic tail (spec, answer, requirements, ledger).
ONE user message (Gemma-family APIs reject/ignore system roles)."""
from __future__ import annotations

import config
from contracts import Artifact, Attack, LedgerDigest

STATIC = """You are one agent in an adversarial red-team swarm. The TARGET is an ANSWER (code, a derivation, or factual claims) written by a different AI, which may contain subtle logical errors. Your job is to BREAK it, but only with CHECKABLE EVIDENCE that a machine will execute. Opinions and assertions are worthless and are discarded.

HARD RULES
1. Every attack carries exactly one evidence object (schema below). No evidence = discarded.
2. Expected values must follow from the SPEC itself, never from guessing how the answer "should" behave. If the SPEC does not determine the result for a case, do NOT attack that case. Inputs must be ones the SPEC allows.
3. PREFER evidence that needs no guessed answer: crashes, hangs, and properties/invariants that must always hold. Machines will also cross-check your expectation against independent implementations, so a wrong expectation scores nothing.
4. Use the exact names (functions, classes) that appear in the answer.
5. Never repeat anything listed under ALREADY TRIED. If requirements R1..Rn are given, start each rationale with the requirement it targets, e.g. "R2: ...".
6. Return at most <<MAX>> attacks, best first; {"attacks": []} if nothing credible.
7. Output ONLY one JSON object. No prose, no markdown fences, no comments."""

EVIDENCE = {
    "code": """EVIDENCE SCHEMA (code). Exactly one of these per attack:
A) PROPERTY (preferred): {"rationale":"...","computation":{"expr":"forall(lists(ints(0,20),8), lambda xs: sorted(f(list(xs))) == sorted(xs))","expected":"True"}}
   helpers: forall(gen, prop, n=200) -> True or a shrunk counterexample; gens: ints(lo,hi) floats() strs(alphabet,max_len) lists(gen,max_len) tuples(g1,g2,...) pairs(lo,hi). A tuples(...) gen spreads into prop's arguments. A property that raises counts as failing.
B) SCENARIO (classes, state, call sequences): {"rationale":"...","computation":{"expr":"c = Cache(2)\\nc.put(1, 1)\\nc.put(2, 2)\\nc.get(1)\\nc.put(3, 3)\\nresult = c.get(2)","expected":"-1"}}   (multi-line snippet; final value in `result`; a single expression also works)
C) SINGLE CALL: {"rationale":"...","test":{"input":"<arguments exactly as typed in a call, e.g. [[1,2],[2,3]]  or  'abc', 3>","expected":"<Python expression | raises ValueError | no_error>"}}
   For programs that read stdin: input = the stdin text, expected = the exact stdout text.
   no_error = the SPEC says this input is valid and must not crash or hang.""",
    "math": """EVIDENCE SCHEMA (math / reasoning). Exactly one of these per attack, as {"rationale":"...","computation":{"expr":"...","expected":"..."}}:
A) RECOMPUTE the answer independently (preferred): expr = a Python expression or multi-line snippet (final value in `result`; itertools, math, fractions available) that computes the answer by exact computation or exhaustive enumeration, e.g. "sum(1 for n in range(1000,10000) if sum(map(int,str(n)))==10)"; expected = the value your code produces. It lands if the answer's final `ANSWER:` differs and independent solvers agree with you.
B) REFUTE a claim: expr's FIRST line is "# claim: <a verbatim span from the answer>", followed by code ending with result = True when it exhibits a concrete counterexample or violated constraint; expected = "True".
C) ARITHMETIC LINE: expr copied verbatim from a line the answer writes as `expr = value`; expected = the CORRECT value.""",
    "factual": """EVIDENCE SCHEMA
{"attacks":[{"rationale":"<=25 words","claimCheck":{"claim":"<ONE atomic claim copied near-verbatim from the answer, including the specific you believe is wrong>","sourceQuery":"<2-6 word encyclopedia search query>"}}]}
Prefer claims you believe reliable sources contradict. If every claim in your ROLE looks right, still submit the 1-2 most specific, most checkable ones in your ROLE: each is checked against sources, and a claim that holds up is what earns the answer trust. Never return an empty list when the answer states a checkable specific in your ROLE.""",
}
SHAPE = 'Wrap attacks as {"attacks":[ ... ]}.'

FOCUS = {
    ("boundary", "code"): "ROLE: INPUT SPACE. Empty/singleton inputs, zero/negatives, extreme sizes, duplicates, ordering (sorted/reversed), equal or touching values, degenerate structures (self-loops, cycles, single node), whitespace/unicode, very large N. Also: inputs the SPEC allows that make the code crash or hang (use no_error).",
    ("numeric_type", "code"): "ROLE: VALUES & REPRESENTATION. Float precision, int/float/bool mixing, nan/inf, huge magnitudes, rounding mode, integer vs true division, string vs bytes/encoding, ALIASING: input or default argument mutated, returned object shared between calls.",
    ("spec_gap", "code"): "ROLE: REQUIREMENTS. For each requirement, craft a probe that fails if it is unmet: unhandled branches, what must raise vs return, ordering/stability, idempotence, state left after an error, return type, non-mutation, call-sequence behaviour of classes.",
    ("factual", "code"): "ROLE: INVARIANTS. Express what must ALWAYS hold as forall properties: round-trips (decode(encode(x)) == x), monotonicity, commutativity/associativity where specified, output is a permutation/subset/superset of input, result agrees with a simple brute-force definition, idempotence, determinism.",
    ("boundary", "math"): "ROLE: RECOMPUTE. Re-derive the final answer independently by brute force or exact computation (enumeration, itertools, Fraction). Do not trust the derivation's method, only its result.",
    ("numeric_type", "math"): "ROLE: DECIMALS & UNITS. Rounding, decimal placement, percent vs fraction, unit conversions, exact vs approximate values in the written steps and the final answer.",
    ("spec_gap", "math"): "ROLE: IGNORED CONSTRAINTS. Constraints in the problem the derivation ignored or mis-applied (ranges, distinctness, ordering, leading zeros, boundary values, double counting). Falsify with exhaustive enumeration of the real problem.",
    ("factual", "math"): "ROLE: UNIVERSAL CLAIMS. Find 'always / for all / never / must / every' claims and unjustified steps; refute with a concrete counterexample snippet (B). Also check derived quantities written as `expr = value`.",
    ("boundary", "factual"): "ROLE: NUMBERS & DATES. Years, dates, counts, measurements, rankings, first/last/largest claims.",
    ("numeric_type", "factual"): "ROLE: UNITS & MAGNITUDES. Units, conversions, percentages, currencies, orders of magnitude.",
    ("spec_gap", "factual"): "ROLE: OVERREACH. Overgeneralisations, causal claims, attributions ('X invented Y'), superlatives, wrongly stated implications.",
    ("factual", "factual"): "ROLE: ENTITIES. Names, places, organisations, titles, and fabricated specifics (invented people, papers, quotes).",
}


def _fmt_attack(a: Attack) -> str:
    if a.test:
        return f"in={a.test.input} -> {a.test.expected}"
    if a.computation:
        return f"{a.computation.expr.splitlines()[0][:80]} -> {a.computation.expected}"
    return a.claim_check.claim  # type: ignore[union-attr]


def build_prompt(role: str, art: Artifact, ledger: LedgerDigest | None, max_attacks: int,
                 requirements: list[str] | None = None) -> str:
    head = "\n\n".join([STATIC.replace("<<MAX>>", str(max_attacks)), EVIDENCE[art.domain], SHAPE,
                        FOCUS[(role, art.domain)]])
    cap = config.LEDGER_PROMPT_CAP
    tried = []
    if ledger and cap > 0:  # cap <= 0 means show none ([-0:] would show the whole list)
        tried += [f"- [survived] {_fmt_attack(a)}" for a in ledger.survivors[-cap:]]
        tried += [f"- [landed earlier, since patched] {_fmt_attack(a)}" for a in ledger.landed[-cap:]]
    reqs = ("\n=== REQUIREMENTS ===\n" + "\n".join(f"R{i}: {r}" for i, r in enumerate(requirements, 1)) + "\n"
            if requirements else "")
    tail = (f"=== SPEC ===\n{art.spec}\n\n=== ANSWER (version {art.version}) ===\n{art.content}\n{reqs}\n"
            f"=== ALREADY TRIED ===\n{chr(10).join(tried) if tried else '(none yet)'}\n\nJSON:")
    return head + "\n\n" + tail
