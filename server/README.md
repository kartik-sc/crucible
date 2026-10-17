# server — FastAPI backend (Render, always-on)

Orchestration loop + Model Gateway + verifiers + model calls. Owners A and B.

```
orchestrator/   # A: loop FSM, coordinator, ledger, gateway, sse
breakers/       # B: builder + 4 breaker roles
verifiers/      # B: pyexec (code/math), nli (factual), scorer
```

Entry: `uvicorn app:app --reload`. Exposes `POST /run` (SSE stream) per CONTRACTS.md.
