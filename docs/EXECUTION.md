# EXECUTION — plan of action & even work split

**How to start building, in dependency order, with work split evenly across 3.**
Refines PLAN.md's ownership into balanced, parallelizable buckets. Gateway is
already built and tested, so it is treated as a fixed dependency.

---

## 1. First 90 minutes (all three, together)

Do these before anyone writes component logic:

1. Create the **public** repo; push the starter bundle (docs + gateway).
2. Each member: make a **Groq account** and an **AI Studio project**; collect
   3 keys per provider into a shared `.env` (never committed).
3. **Freeze CONTRACTS.md** — read it aloud, all three sign off. No field changes after this without telling the other two.
4. Run `python test_rotation.py` (passes with no keys) and `python smoke_test.py`
   (real keys) — proves both pools before the loop exists. Resolve OTQ-1 (Gemma 4 slug + concurrency) here.
5. M1 commits a **mock SSE emitter** (emits a scripted event sequence per CONTRACTS §4). This single file unblocks M3 to build the entire UI with no backend.
6. Deploy an empty frontend + a `/health` backend to the live URLs so hosting surprises happen now.

After this, the three tracks run in parallel.

## 2. Even work split (~20 effort-points each)

### M1 — Engine (control plane)
Loop FSM · Coordinator (fan-out/dedup/novelty) · Attack Ledger · Heavy-Answer
Gate · Scorer · signature/normalization · Verifier Router (interface) · FastAPI
`/run` SSE endpoint · `/health` + `/usage` · **backend deploy (Render)** · the
mock SSE emitter.
> Pure orchestration, no LLM prompts, no UI. Consumes the Gateway (done) and M2's agents/verifiers behind their interfaces.

### M2 — Intelligence & Ground Truth
Builder (generate + patch prompts) · Breaker scaffold + the 4 role prompts
(boundary / numeric_type / spec_gap / factual) + parse/validate/repair/drop ·
PyExec verifier (code + math sandbox) · NLI verifier (retrieval + DeBERTa) · the
**3 pre-staged planted-flaw demo artifacts**.
> Everything that calls a model or checks truth. Hardest prompt-engineering (the swarm = the O1 differentiator); demo artifacts live here because M2 knows what the system catches.

### M3 — Experience
The whole Next.js arena: split-screen (builder | swarm) · SSE client + state ·
robustness dial (animated) · round timeline · attack-stream rows + strike/patch
visuals · domain toggle + query input · Pyodide mirror · judge-live mode ·
styling/polish · **frontend deploy (Vercel)** · README polish for judging · demo
script + rehearsal + backup video.
> Cohesive, judge-facing, separable. Builds entirely against the mock SSE stream until integration.

**Parity note:** M1 is highest *volume* but mechanical; M2 is highest *difficulty*
(balanced by getting the lighter demo-artifact task); M3 is broadest *surface* but
lower per-task difficulty (carries demo + deploy). Roughly equal hours.

## 3. Dependency graph (what unblocks what)

```
CONTRACTS (done) + GATEWAY (done)
   |            |                 |
   v            v                 v
 M1 mock SSE   M2 builds agents   (shared types)
   |            + verifiers on
   v            the live gateway
 M3 builds full UI      |
 on mock SSE            v
   |            M1 wires loop -> calls M2 agents/verifiers
   |                     |
   +----- integrate -----+----> MUST-HAVE (one real round, streamed to real UI)
```

- **Nobody is blocked at the start.** M3 ← mock SSE; M2 ← gateway; M1 ← contracts.
- **Critical path = M1 loop ↔ M2 agents/verifiers** meeting for the MUST-HAVE.
- M3 integrates by swapping the mock SSE URL for the real `/run` — contract-identical.

## 4. Milestones & Definition of Done

| # | Milestone | Done when | Tier |
|---|---|---|---|
| M0 | Scaffold | repo public, contracts frozen, both pools smoke-tested, empty URLs live | — |
| M1 | One real round | Builder→1 breaker→verifier→patch→score runs and streams to the real UI on the deployed URL | **MUST-HAVE** |
| M2 | The swarm | 4 specialized breakers, multi-round loop, dedup, robustness dial climbing | **WOW** |
| M3 | Domains + polish | factual + math domains live; strike/patch animation; styling | **WOW** |
| M4 | Finale | judge-live mode, 3 planted artifacts rehearsed, backup video, **submit by 3:00** | **FINALE** |

## 5. Integration seams (freeze these, mock across them)

| Seam | Owner → Consumer | Contract |
|---|---|---|
| Gateway | (done) → M1/M2 | `gateway.call/builder/breaker_fanout` |
| SSE stream | M1 → M3 | CONTRACTS §4 events |
| Verifier Router | M1 → M2 adapters | `(artifact, attack) → Verdict` |
| Ledger digest | M1 → M2 breakers | `{tried, survivors, landed}` |
| Agent calls | M2 → M1 loop | Builder/Breaker interfaces (CONTRACTS §2) |

## 6. Parallel timeline (everyone busy every window)

| Window | M1 | M2 | M3 |
|---|---|---|---|
| Sat AM | mock SSE, FSM skeleton, /run stub | Builder + 1 breaker on gateway | arena layout + SSE client on mock |
| Sat PM | Coordinator + Ledger + Scorer; wire 1 round | 4 breakers + PyExec | dial + timeline + attack rows |
| Sat eve | multi-round loop; integrate M2 | NLI + factual domain | strike/patch visuals; integrate real SSE |
| Sat night | dedup + convergence; backend deploy | math domain + planted artifacts | polish + frontend deploy |
| Sun AM | harden loop; /health,/usage | demo artifacts final; bug-bash | judge-live mode; demo script + video |

## 7. Rebalancing rule

Tiers are prioritized so the team converges on the critical path. If a member
finishes their tier early, they move to **M2's agent work or the integration
seam** (the critical path), not to polish. Never let one person idle while the
MUST-HAVE is incomplete.

## 8. Pre-build checklist (consolidated)

- [ ] Public repo + starter bundle + gateway pushed
- [ ] 3 Groq + 3 AI Studio keys per `.env` (uncommitted)
- [ ] CONTRACTS.md frozen, all three signed off
- [ ] `test_rotation.py` passes; `smoke_test.py` returns text from both pools
- [ ] OTQ-1 resolved: Gemma 4 slug + per-project concurrency confirmed (≥ the 4-way burst)
- [ ] Mock SSE emitter committed (unblocks M3)
- [ ] Empty frontend + `/health` backend deployed to live URLs
- [ ] Each member knows their bucket and the seams they mock across
