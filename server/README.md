# server — CRUCIBLE backend components

The server package contains the reusable backend pieces for the orchestration
loop. The FastAPI entrypoint and loop FSM are not part of this integration yet.

```
orchestrator/   # contracts, configuration, gateway, parsing, signatures
breakers/       # builder, LLM breakers, deterministic auditors, oracles
verifiers/      # sandbox execution, static lints, factual NLI
demo/           # deterministic fixtures used by the smoke script and tests
```

The public integration points are:

- `crucible.server.breakers.builder.Builder`
- `crucible.server.breakers.breakers.make_swarm`
- `crucible.server.breakers.auditors.make_auditors`
- `crucible.server.breakers.oracles.LLMOracles`
- `crucible.server.verifiers.pyexec.PyExecVerifier`
- `crucible.server.verifiers.nli.NLIVerifier`
- `crucible.server.orchestrator.contracts`

The future FastAPI `/run` endpoint should call these components through the
contracts documented in `docs/CONTRACTS.md`.
