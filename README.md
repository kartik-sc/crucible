<h1 align="center">CRUCIBLE</h1>
<p align="center"><b>Trust infrastructure for AI outputs.</b><br>
Code goes in. Adversaries hammer it. Only what survives reaches you.</p>

<p align="center">
Hacktoberfest Hack Day Bengaluru 2026 &middot; Track 2 — Best Open-Source AI Project<br>
Primary approach: <b>O1 Autonomous Agent Swarms</b> (+ O3 Trustworthy &amp; Verifiable AI)
</p>

---

## The problem

LLMs give confident answers that are subtly wrong — a broken edge case, a
fabricated citation, an arithmetic slip — and you usually **cannot tell which**.
Scoring the final answer is not enough; the failure hides inside it.

## What CRUCIBLE does

CRUCIBLE puts a heavy answer on trial. A **Builder** agent produces it; a
**swarm of four specialized adversary agents** attacks it — each attack carrying
**checkable evidence** (a failing test, a computation, a claim + source). Every
attack is settled by a **verifier that executes code/math or runs entailment on
sources — never by another model's opinion**. Verified failures go back to the
Builder, which patches. The loop repeats until a round lands zero new breaks.

You get the hardened answer, a **robustness score**, and a visible attack trace.

> The one rule: a breaker never wins by assertion. No evidence, no strike.

## How it works

```
query -> Heavy-Answer Gate -> Builder -> Breaker swarm (x4, parallel)
      -> Verifier (execute / entail) -> Scorer -> patch -> loop (<= 4 rounds)
```

See [ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the full diagram and module map.

## Domains

| Domain | Attacks for | Ground truth |
|---|---|---|
| Code | edge cases / failing inputs | sandboxed Python runs the test |
| Math | arithmetic / unit / logic errors | Python computes the answer |
| Factual | unsupported / contradicted claims | retrieval + DeBERTa-v3-MNLI entailment |

## Stack

- **Frontend:** Next.js (Vercel) — arena, robustness dial, Pyodide mirror
- **Backend:** FastAPI (Render) — orchestration loop, model gateway, verifiers
- **Models (open-weight):** Builder = Qwen3-32B (Groq) &middot; Breaker swarm = Gemma 4 (Google AI Studio) &middot; Factual verifier = DeBERTa-v3-MNLI

## Run locally

```bash
cp .env.example .env     # fill in your keys
# backend
cd server && pip install -r requirements.txt && uvicorn app:app --reload
# frontend
cd web && npm install && npm run dev
```

## Live demo

> TODO: deployed URL here before submission.

## Team

> TODO: three contributors.

## License

MIT — see [LICENSE](./LICENSE).
