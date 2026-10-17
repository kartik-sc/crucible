# TRD — CRUCIBLE

**Technical Requirements Document · v1 · pre-build**
Reads with ARCHITECTURE.md (system diagram + decisions) and CONTRACTS.md
(interfaces). This doc states per-component requirements, the API, non-functional
budgets, and acceptance tests. Requirement IDs: TR-x.

---

## 1. Architecture summary

Next.js frontend (Vercel) ⇄ FastAPI orchestrator (Render, always-on) → hosted
open-weight models + deterministic verifiers. One request runs a bounded
attack/patch loop and streams every step over SSE. Full diagram: ARCHITECTURE.md.

## 2. Component requirements

For each: responsibility · I/O (per CONTRACTS.md) · requirements · acceptance test.

### 2.1 Model Gateway  — **DONE**
- Provider abstraction + key-pool rotation + least-inflight breaker fan-out + usage meter.
- TR-1 rotate on 429/5xx/timeout only; fail-fast on 4xx. **(proven by test_rotation.py)**

### 2.2 Heavy-Answer Gate  (M1)
- Decide if an input enters the loop.
- TR-2 no LLM call; decide from claim count / step count / code length.
- TR-3 below threshold → answer once, skip loop.
- Accept: a one-line factual query skips; a multi-claim answer enters.

### 2.3 Loop Engine / FSM  (M1)
- Own the round lifecycle and stop conditions.
- TR-4 states GENERATE→FANOUT→VERIFY→SCORE→DECIDE→{PATCH|DONE}; one SSE event per transition.
- TR-5 stop when round==MAX_ROUNDS(4) OR newVerifiedBreaks==0.
- TR-6 any component error → emit ERROR event, freeze last good version, never crash the stream.
- Accept: a scripted artifact runs to DONE with correct stop reason.

### 2.4 Coordinator  (M1)
- Parallel fan-out to breakers; dedup; novelty gate.
- TR-7 call `gateway.breaker_fanout`; `allSettled` semantics (one breaker failing ≠ round failure).
- TR-8 dedup incoming attacks by signature against the Ledger BEFORE verify/score.
- Accept: duplicate signatures from two breakers are verified once.

### 2.5 Attack Ledger  (M1)
- Shared swarm memory; append-only signatures + verdicts; digest for breakers.
- TR-9 `digest()` returns `tried` (signatures only), `survivors`, `landed` per CONTRACTS.
- TR-10 signature = normalized hash per domain (code: normalized input; math: canonical expr; factual: lemmatized claim).
- Accept: a breaker that receives the digest does not re-emit a tried signature.

### 2.6 Builder  (M2)
- Author the answer and patch it from failing verdicts.
- TR-11 generate: (spec) → {content, assumptions[]}. patch: (artifact, landedVerdicts[]) → content'.
- TR-12 patch prompt carries ONLY failing tests + actuals (delta-only); survivors not resent.
- TR-13 one patch call per round (batched), via `gateway.builder`.
- Accept: given 2 failing tests, the patched content passes both without breaking survivors.

### 2.7 Breaker swarm (4 roles)  (M2)
- One scaffold, four roles by prompt+temp+seed, each emitting evidence-bearing attacks.
- TR-14 roles: boundary, numeric_type, spec_gap, factual — exclusive attack surfaces.
- TR-15 **evidence rule:** an Attack with no test/computation/claimCheck is dropped at validation.
- TR-16 pipeline: ledger-aware prompt → model → parse JSON → ONE repair retry → drop if still invalid.
- TR-17 ≤ MAX_ATTACKS_PER_BREAKER (4) per role per round; read ledger digest to avoid repeats.
- Accept: each role returns ≥1 schema-valid, novel, evidence-bearing attack on a seeded artifact; malformed output is dropped, not crashed.

### 2.8 Verifier Router + adapters  (M1 router, M2 adapters)
- Settle each attack by execution or entailment — never an LLM opinion.
- TR-18 route by attack type: test/computation → PyExec; claimCheck → NLI.
- TR-19 **PyExec**: sandboxed Python, no network, ≤2s timeout, memory-capped; returns Verdict {landed, actual, evidence}.
- TR-20 **NLI**: retrieve `sourceQuery` → DeBERTa-v3-MNLI entailment; landed = CONTRADICTED or UNSUPPORTED; evidence = label + span.
- Accept: a known-failing test returns landed=true with the actual output; a contradicted claim returns landed=true with the source span.

### 2.9 Scorer  (M1)
- Verdicts → robustness.
- TR-21 robustness = Σ(survived·w)/Σ(verified·w); w: spec_gap=1.5, factual=1.5, numeric_type=1.2, boundary=1.0.
- TR-22 a patch flips prior landed→survived so the dial is monotonic as hardening proceeds.
- Accept: scripted verdicts across 3 rounds produce a rising score.

### 2.10 API / SSE endpoint  (M1)
- Expose the loop as a streaming HTTP endpoint (see §3).
- TR-23 `POST /run` streams SSE events per CONTRACTS §4 until DONE/ERROR.
- Accept: a curl against /run yields a well-formed event sequence ending in DONE.

### 2.11 Frontend arena  (M3)
- Render the stream legibly; drive the demo.
- TR-24 consume SSE; render builder pane, attack rows, verdicts, robustness dial, round timeline.
- TR-25 color grammar: green=survived, amber=unsupported, red=contradicted/struck.
- TR-26 Pyodide mirror runs the demo code client-side for the audience (authoritative result is still server-side PyExec).
- TR-27 domain toggle + query input; judge-live mode.
- Accept: against the mock SSE stream, the full arena animates end to end with no backend.

## 3. API specification

```
POST /run                      # start a crucible run (SSE response)
  body: { "query": string, "domain": "code"|"factual"|"math" }
  resp: text/event-stream of CONTRACTS §4 events:
        STATE, BUILDER, ATTACK, VERDICT, SCORE, ROUND_END, DONE, ERROR

GET  /health                   # { ok, pools: [...] }  (key-pool snapshot, masked)
GET  /usage                    # gateway.usage.summary() for the live budget meter
```

- Content type for /run: `text/event-stream`; one JSON payload per event.
- CORS: allow the Vercel origin only.
- No auth (non-goal N1); keys live server-side only.

## 4. Data model

Canonical in CONTRACTS.md: `Artifact`, `Attack` (with one of test/computation/claimCheck),
`Verdict`, `LedgerDigest`. Backend = Pydantic, frontend = TS; keep both in sync with CONTRACTS.

## 5. Non-functional requirements

| ID | NFR | Target |
|---|---|---|
| NFR-1 | Per-round latency | feels live; small payloads, delta-only messaging |
| NFR-2 | Token/run | ~48k (≈12k/round); verification offload keeps 0 LLM on code/math |
| NFR-3 | Breaker concurrency | 4 parallel, spread least-inflight across the key pool |
| NFR-4 | Reliability | rotation on 429/5xx; ERROR event never crashes the stream |
| NFR-5 | Security | keys never in client or repo; `.env` gitignored; sandbox no-network |
| NFR-6 | Observability | /health pools, /usage meter, one SSE event per FSM transition |
| NFR-7 | Determinism of verdicts | code/math by execution; author never grades itself |

## 6. Deployment topology

- **Frontend:** Next.js on Vercel (static/SSR). Env: `WEB_PUBLIC_API_URL`.
- **Backend:** FastAPI on Render **Web Service** (always-on) — chosen to avoid
  serverless function timeouts on the multi-round loop. Env: see .env.example.
- **Models:** hosted free-tier APIs (Groq, AI Studio) via the Gateway.
- **Factual model:** HF Inference API or a small in-process route.

## 7. Error handling / edge cases

| Case | Handling |
|---|---|
| Gateway exhausted (pool cooling) | ERROR event; freeze last good version; UI shows "rate-limited, retrying" |
| Breaker returns no valid attacks | treat as zero new breaks for that role; may trigger convergence |
| All attacks dedup to empty | round contributes nothing → DECIDE → converge |
| Verifier timeout | that attack = indeterminate (not landed); logged; loop continues |
| Malformed breaker JSON | parse → one repair → drop; never crash the round |
| Empty/converged round 1 | legitimate DONE with reason=converged |

## 8. Open technical questions (resolve on day 0)

- OTQ-1 Exact Gemma 4 slug + per-project RPM/concurrency on AI Studio (the #1 demo risk).
- OTQ-2 NLI model + hosting (HF Inference vs in-process DeBERTa).
- OTQ-3 Retrieval provider for the factual domain (Tavily vs Brave).
- OTQ-4 PyExec authority: server-side jailed Python is authoritative; Pyodide is the browser mirror — confirm the server path early.

## 9. Test strategy

- **Unit:** Gateway (done), Scorer, dedup/signatures, each verifier adapter.
- **Integration:** one full round (Builder→1 breaker→verifier→patch→score).
- **E2E:** the demo script on the deployed URL, plus the three planted-flaw artifacts.
- **Principle:** the verifier that decides an attack is never the model that authored the answer.
