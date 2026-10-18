# server — FastAPI backend (Render, always-on)

Orchestration loop + Model Gateway + verifiers + model calls. Owners A and B.

```
app.py          # A: POST /run (SSE), /mock/run, /health, /usage
contracts.py    # Pydantic mirror of docs/CONTRACTS.md (camelCase on the wire)
config.py       # loop constants + settings from env
orchestrator/   # A: loop FSM, coordinator, ledger, gate, signatures, events
  agents.py     #    the M1<->M2 seam: Builder / Breaker / VerifierAdapter protocols
  fakes.py      #    scripted planted-flaw agents for all 3 domains (no keys)
  wiring.py     #    fake vs real agents — M2 plugs in here
breakers/       # B: builder + 4 breaker roles
verifiers/      # A: router + scorer · B: pyexec (code/math), nli (factual)
tests/          # acceptance tests per TRD §2
```

## Run

```bash
uv venv .venv && uv pip install -p .venv -r requirements-dev.txt
.venv/bin/uvicorn app:app --reload          # CRUCIBLE_AGENTS=fake by default
.venv/bin/python -m pytest -q
curl -N -X POST localhost:8000/run -H 'content-type: application/json' \
  -d '{"query":"Return the nth Fibonacci number, n >= 0.","domain":"code"}'
```

`GET /mock/run?domain=code|math|factual` streams the same events from scripted
agents. M3 can build the whole arena against it with a plain `EventSource`.

## Plugging in M2 (`orchestrator/wiring.py`)

Implement the protocols in `orchestrator/agents.py` (sync or async both work):

- `builder.generate(spec, domain) -> BuildResult` · `builder.patch(artifact, breaks: list[LandedBreak]) -> str`
- `breaker.attack(spec, content, weakness_class, digest) -> list[Attack | dict]`. `id`
  and `signature` are optional; the Coordinator assigns them and drops anything
  without exactly one evidence payload.
- `verifier.verify(artifact, attack) -> Verdict | dict`, registered by evidence kind:
  `{"test": pyexec, "computation": pyexec, "claimCheck": nli}`

Then return them from `build_agents()` and set `CRUCIBLE_AGENTS=real`.

## M2 components (intelligence & ground truth)

The reusable backend pieces M2 contributes, ported onto this layout (absolute
imports, `server/` as the root — the modules live here, not under a `server`
package):

```
breakers/   # builder, LLM breakers, deterministic auditors, oracles
verifiers/  # sandbox execution (pyexec), static lints, factual NLI
demo/       # deterministic planted-flaw fixtures for the smoke script and tests
```

Public integration points (wired in `orchestrator/wiring.py`):

- `breakers.builder.Builder`
- `breakers.breakers.make_swarm`
- `breakers.auditors.make_auditors`
- `breakers.oracles.LLMOracles`
- `verifiers.pyexec.PyExecVerifier`
- `verifiers.nli.NLIVerifier`

All types come from the single `contracts.py`; configuration from `config.py`;
signatures/ids are assigned by the Coordinator, not by the breakers.
