# PLAN — ownership, timeline, execution

## Stack decision to CONFIRM in hour 0

Recommended: **Python (FastAPI) backend on Render** = orchestrator + gateway +
verifiers + model calls; **Next.js (TS) frontend on Vercel** = UI + SSE + Pyodide
mirror. Two deployables, Python where the ML/exec lives, TS where the UI lives.
If the team prefers an all-TS backend, the only change is the verifier service
(Python sidecar for exec + NLI). Decide before the first logic commit.

## Owners

| Owner | Workstream | Deliverables |
|---|---|---|
| **A — Orchestration** | loop FSM, coordinator, ledger, Model Gateway + key rotation, SSE | the engine + the /run endpoint |
| **B — Agents + Verify** | 4 breaker roles, builder/patch, PyExec + NLI verifiers, scorer | the intelligence + the ground truth |
| **C — Frontend + Demo** | arena split-screen, dial, timeline, SSE client, Pyodide mirror, demo inputs, README | what the judges see |

Shared seam: A builds the **Gateway interface**, B consumes it. Freeze
CONTRACTS.md first so A/B/C mock each other.

## Timeline (submit Sunday by 3:00 PM, not 3:30)

| Window | Build | Tier |
|---|---|---|
| Sat, first hour | Public repo + MIT + .gitignore + .env.example, freeze CONTRACTS, **deploy a hello-world to the live URL today** | — |
| Sat day | One full round end-to-end: builder -> 1 breaker -> verifier -> patch -> score, rendered | **MUST-HAVE** |
| Sat eve | Fan-out to 4 specialized breakers (the swarm), multi-round loop, robustness dial | **WOW** |
| Sat night | Attack animation, round timeline, strike-and-patch visuals; add factual + math domains | **WOW** |
| Sun 9:30-2:30 | Judge-proposes-input live mode, bug-bash, backup demo video, SUBMIT 3:00 | **FINALE** |

## Domain rollout (phased — do NOT build all at once)

- **Must-have (Sat):** code (Pyodide/Python) + factual (retrieval + NLI).
- **Wow (Sat night):** math verifier (cheap, visually crisp).
- **Flex (Sun):** reasoning verifier (counterexample-or-it-does-not-count) — only if core is solid.

## Cut order if behind

Judge-live mode -> extra breaker -> drop to 2 breakers -> single round with a
visible attack list. **NEVER cut** the execute-and-patch loop or the robustness
dial — those ARE the demo.

## Day-0 checklist (do before writing loop logic)

- [ ] Confirm stack (Python backend + Next.js front).
- [ ] Create **public** GitHub repo, add LICENSE/.gitignore/.env.example/README skeleton.
- [ ] Freeze CONTRACTS.md; all three sign off.
- [ ] Each teammate: create a Groq account + an AI Studio project; collect 3 keys per provider.
- [ ] **Read AI Studio console: Gemma 4 RPM + concurrency per project** (the #1 demo-risk unknown).
- [ ] Confirm exact model slugs (Groq Qwen3-32B, AI Studio Gemma 4) — they are NOT identical weights across providers.
- [ ] Smoke-test the Model Gateway (one Qwen call + one Gemma call + a forced-429 rotation) BEFORE building the loop.
- [ ] Deploy an empty shell to the live URL so hosting surprises happen now.

## Top risks

| Risk | Mitigation |
|---|---|
| Gemma 4 free-tier concurrency caps the 4-way burst | spread across 3 keys least-inflight; drop to 2 breakers if needed |
| Gemma JSON malformed at high temp | parse -> one repair retry -> drop; measure hit rate day 0 |
| Live demo network flakiness | record a backup demo video Sunday morning |
| Loop runs long / spins the dial slowly | MAX_ROUNDS=4, early-exit on zero-new-breaks, small payloads |

## Judging adjustments (panel: 2 non-ML, 1 DevRel, 1 PM, 1 DS)

- Open the pitch with the **problem** ("you cannot tell which AI claims are wrong"), not the architecture.
- Frame as **trust infrastructure any developer can adopt** (Roshan, Pritesh).
- Treat **README + repo as judged artifacts** (Pritesh, Rekha): diagram, clean setup, MIT, visible 3-person commit history.
- Keep **one ML-depth answer** loaded for Akash: decorrelation, verification-vs-LLM-judging, the score formula.
- Make **execution visible** for Anubhav: working live URL, real commits from all three.
