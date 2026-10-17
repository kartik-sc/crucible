# PRD — CRUCIBLE

**Product Requirements Document · v1 · pre-build**
Hacktoberfest Hack Day Bengaluru 2026 · Track 2 (Best Open-Source AI Project).

---

## 1. Problem

LLMs produce confident answers that are subtly wrong — a broken edge case, a
fabricated citation, an arithmetic slip — and the reader usually cannot tell
which parts to trust. Scoring a final answer as a whole hides the failure inside
it. There is no accessible, open tool that **stress-tests an AI answer and shows,
with evidence, exactly what survives scrutiny.**

## 2. Goals / Non-goals

**Goals**
- G1. Take any "heavy" answer and harden it by adversarial attack + author rebuttal.
- G2. Make every attack **objective** — settled by execution or entailment, never by an LLM's opinion.
- G3. Make the process **legible** — a judge understands it in under two minutes.
- G4. Demonstrate a real **agent swarm** (Track 2 / O1) and **verifiability** (O3).
- G5. Run on a **public live URL** judges can test themselves.

**Non-goals (explicitly out of scope for the hackathon build)**
- N1. User accounts, auth, multi-tenant, persistence across sessions.
- N2. Training or fine-tuning any model.
- N3. A production SLA, horizontal scale, or billing.
- N4. Supporting every answer type — only code, factual, and math (math is stretch).
- N5. Beating SOTA hallucination benchmarks; this is a system, not a paper.

## 3. Users

| Persona | Need | What they judge CRUCIBLE on |
|---|---|---|
| **Developer** (the product's user) | a verification layer to put in front of any LLM output | does it catch real errors; could I adopt it |
| **Hackathon evaluator** | assess technical merit, clarity, value in a short demo | is the mechanism real, is it clear, does it work live |

Evaluator sub-lenses (the actual panel): engineering soundness, project execution,
ML rigor, real-world/open value, and communication clarity. The product must land
on all five, not only the ML one.

## 4. User stories

- As a developer, I paste a heavy answer (or ask a question) and get back a
  **hardened version** with struck claims and a trust score, so I know what to rely on.
- As a developer, I see **why** a claim was struck — the failing test or the
  contradicting source — so the verdict is checkable, not asserted.
- As a developer, I switch domains (code / factual / math) and the same engine
  attacks the right way for each.
- As a judge, I type my **own** input and watch the crucible break and fix it live,
  so I trust the demo is not canned.

## 5. Functional requirements (MoSCoW → build tier)

| ID | Requirement | Priority | Tier |
|---|---|---|---|
| FR-1 | Accept a query/answer + domain; gate out trivial inputs | MUST | MUST-HAVE |
| FR-2 | Builder agent produces/patches an answer | MUST | MUST-HAVE |
| FR-3 | Breaker swarm (≥1, target 4) emits evidence-bearing attacks | MUST | MUST-HAVE |
| FR-4 | Every attack settled by a verifier (exec / entailment), never an LLM opinion | MUST | MUST-HAVE |
| FR-5 | Loop: verified failures → patch → re-attack, ≤4 rounds, stop on zero-new-breaks | MUST | MUST-HAVE |
| FR-6 | Compute + display a robustness score; show the hardened answer | MUST | MUST-HAVE |
| FR-7 | Stream the whole process to the UI (attacks, verdicts, patches) live | MUST | WOW |
| FR-8 | Code domain (Pyodide/Python exec) | MUST | MUST-HAVE |
| FR-9 | Factual domain (retrieval + NLI entailment) | SHOULD | MUST-HAVE |
| FR-10 | Math domain (computation check) | SHOULD | WOW |
| FR-11 | Judge-live mode: evaluator types their own input | SHOULD | FINALE |
| FR-12 | Reasoning domain (counterexample-required) | COULD | FLEX |

## 6. Scope: MVP vs stretch

- **MVP (must demo):** FR-1..6, FR-8, FR-9 — one engine, two hard-ground-truth
  domains, the loop, the dial. This alone is a complete, winning Track-2 entry.
- **Stretch (adds wow):** FR-7 live streaming visuals, FR-10 math, FR-11 judge-live.
- **Flex (only if core is solid):** FR-12 reasoning.

## 7. Acceptance criteria

The demo **is** the acceptance test. The build is "done enough" when, on the live URL:

1. A pre-staged heavy answer with one planted flaw is submitted.
2. The swarm attacks; ≥1 attack **lands with visible evidence**; the rest pass.
3. The failure feeds back; the Builder **patches**; the struck claim is removed/fixed.
4. The **robustness dial climbs** and the round state is shown.
5. A judge submits **their own** input and the same thing happens (FINALE).

Per-FR acceptance lives in TRD.md as component acceptance tests.

## 8. Success metrics

| Metric | Target |
|---|---|
| Catches the planted flaw in the demo | 100% (pre-staged, rehearsed) |
| Full run latency (4 rounds) | feels live; dial moves within seconds/round |
| Runs on the public live URL during judging | yes, with a backup video |
| Judge can restate what it does after the demo | yes (clarity test) |
| Open-weight models used meaningfully | Builder + 4-agent swarm + verifier |

## 9. Constraints (hackathon, fixed)

- Public GitHub repo + working live deployment URL required.
- Exactly one track + one primary problem statement (Track 2 / O1).
- Submit by 3:30 PM IST Sun 18 Oct (we target 3:00). Dev window 13–18 Oct.
- Team of 1–3 (we are 3).
