# Model Gateway (pooled)

The only module that touches model providers. Everything else calls
`await gateway.call(role, messages, ...)` and never learns that keys, rotation,
or providers exist.

## Wiring

| Role | Provider | Model env var | Temp | Keys |
|---|---|---|---|---|
| `builder` | Groq | `GROQ_BUILDER_MODEL` | 0.2 | `GROQ_API_KEYS` pool (fallback `GROQ_API_KEY`) |
| `breaker` | Google AI Studio | `AISTUDIO_BREAKER_MODEL` | 0.9 | `AISTUDIO_API_KEYS` pool (fallback `GEMINI_API_KEY`) |

## Behaviour

- **Rotate on** 429 / 5xx / timeout → cool the key, try the next.
- **Auth fail (401/403)** → long-cool that key, try the next.
- **Bug (400/404/422)** → fail fast, do **not** rotate.
- **Breaker fan-out** → `breaker_fanout([...])` runs N calls concurrently, each
  acquiring the **least-inflight** key.
- **Usage** → `gateway.usage.summary()` for the live budget meter.
- **AI Studio** → `seed` is never sent (400s there); breaker calls request
  `generationConfig.responseMimeType="application/json"`; system text is folded
  into the first user turn.
- **Qwen** → Groq calls set `reasoning_format="hidden"` so reasoning tags do
  not enter the returned content.

## Files

```
__init__.py       public surface and M1 compatibility exports
adapter.py        pooled-to-DevGateway compatibility adapter
config.py         build_gateway() from env
gateway.py        ModelGateway: call(), retry/rotate, usage meter, breaker_fanout
keypool.py        KeyPool: least-inflight selection + cool-downs
providers.py      GroqProvider, AIStudioProvider (+ CallResult, Usage)
errors.py         retry/rotate taxonomy
test_rotation.py  mock-transport proof — NO network, NO keys
smoke_test.py     real calls with your keys
```

## Run

```bash
python test_rotation.py   # -> ALL PASSED (no keys)
python smoke_test.py      # real pools; needs server/.env
```

## Integration (A3)

Wire behind `wiring.get_gateway()` with `GATEWAY=dev|pooled`, via the thin
adapter in `adapter.py`. Both provider-specific output controls are enforced at
the provider boundary.
