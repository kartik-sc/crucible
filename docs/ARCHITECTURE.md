# ARCHITECTURE

CRUCIBLE hardens any heavy answer — code, facts, math — by having a swarm of
adversary agents attack it with **checkable evidence** while the author agent
rebuts, looping until the attacks stop landing.

- **Hackathon:** Hacktoberfest Hack Day Bengaluru 2026 (18 Oct, Startup Park).
- **Track 2 — Best Open-Source AI Project.** Primary approach **O1 Autonomous
  Agent Swarms**; secondary flavor **O3 Trustworthy & Verifiable AI**.
- **Pitch framing (for judges):** *trust infrastructure for AI outputs* — a
  verification layer any developer can put in front of an LLM.

## Data flow (one pass)

```
CLIENT (Next.js on Vercel) — the live deploy URL judges test
  domain toggle | arena split (builder | swarm) | robustness dial |
  round timeline | Pyodide mirror (audience view)
      |  query + domain                 ^  SSE (STATE/ATTACK/VERDICT/SCORE)
      v                                 |
ORCHESTRATOR (FastAPI on Render — always-on, no serverless timeout)
  Heavy-Answer Gate -> Loop Engine (FSM) -> Coordinator ("queen")
     GENERATE -> FANOUT -> VERIFY -> SCORE -> DECIDE -> PATCH / DONE
      |                                 |
      v                                 v
  BUILDER (Groq Qwen3-32B, 0.2)   BREAKER SWARM (AI Studio Gemma 4 x4, 0.9)
   { content, assumptions }        boundary | numeric_type | spec_gap | factual
      ^ patch                             |  Attack[] (JSON, evidence required)
      |                                   v
      |                           VERIFIER ROUTER
      |   code/math -> sandboxed Python   factual -> DeBERTa-v3-MNLI
      +------ verified failures ----------+--> SCORER -> robustness dial
```

## Modules

| Module | Owner | Job |
|---|---|---|
| Heavy-Answer Gate | A | Keep trivial answers out of the loop (no LLM) |
| Loop Engine (FSM) | A | Round lifecycle; stop at round 4 OR zero-new-breaks |
| Coordinator (queen) | A | Parallel fan-out; dedup by signature before spend |
| Attack Ledger | A | Shared swarm memory; breakers read it to avoid repeats |
| Model Gateway | A | Only place touching providers; key rotation; usage |
| Builder | B | Author + patch (Groq Qwen3-32B) |
| Breaker swarm x4 | B | One scaffold, four roles by prompt+temp+seed (Gemma 4) |
| Verifier Router | B | PyExec (code/math), NLI (factual) — never an LLM opinion |
| Scorer | B | Weighted survived / verified -> robustness |
| Arena UI + demo | C | Split-screen, dial, timeline, SSE client, Pyodide mirror |

## Deterministic decisions (do not re-litigate)

| Decision | Value |
|---|---|
| Builder model | Groq **Qwen3-32B** (free tier), temp 0.2 |
| Breaker model | Google AI Studio **Gemma 4** (free tier), temp 0.8-1.0, x4 by role |
| Builder != Breaker family | REQUIRED — decorrelated blind spots; author never grades itself |
| Code/math verifier | Sandboxed Python (2s timeout, no network) + Pyodide browser mirror |
| Factual verifier | DeBERTa-v3-MNLI entailment |
| MAX_ROUNDS | 4 |
| Stop condition | round == 4 OR newVerifiedBreaks == 0 |
| Breaker concurrency | 4 parallel, spread least-inflight across the key pool |
| maxAttacks / breaker / round | 4 |
| Patch calls / round | 1 (batched) |
| Keys | pools of 3 legitimate accounts/provider; rotate on 429/5xx only |
| Hosting | frontend Vercel/Render; orchestrator Render (always-on); models hosted free tier |
| Dropped | OpenRouter, Sarvam, local hosting |

## Latency discipline (hosted = keep the demo fast, cost is cents)

1. **Verification offload** — code/math by subprocess, facts by small NLI: 0 LLM.
2. **Delta-only messaging** — send current artifact + ledger signatures, never history.
3. **Batched patch** — one builder call per round.
4. **Dedup before spend** — duplicate signatures die before verify/score.
5. **Max breaker concurrency** — the top latency lever now that we are hosted.
