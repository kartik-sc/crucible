# CONTRACTS — frozen interfaces

> **This is the most important document in the repo.** Freeze it in hour 1 and
> have all three owners sign off. Everyone builds against these mocks in
> parallel; integration becomes wiring, not negotiation. Do not change a field
> without telling the other two owners.

CONTRACTS.md is the single source of truth. The backend expresses these as
Pydantic models, the frontend as TypeScript interfaces. The JSON shape below is
canonical; keep both sides in sync with it.

---

## 0. Enums

```
Domain        = "code" | "factual" | "math"
WeaknessClass = "boundary" | "numeric_type" | "spec_gap" | "factual"
Verdict.label (code/math) = "pass" | "fail"
NLI.label     (factual)   = "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED"
```

---

## 1. Shared types

### Artifact — the thing under attack

```jsonc
{
  "domain": "code",
  "spec": "Return the nth Fibonacci number, n >= 0.",
  "specHash": "sha256:...",        // spec is static -> hash, never re-sent raw
  "content": "def fib(n): ...",    // code | answer prose | derivation
  "assumptions": ["n is an int"],
  "version": 0                      // bumps on every patch round
}
```

```ts
// frontend
export interface Artifact {
  domain: Domain;
  spec: string;
  specHash: string;
  content: string;
  assumptions: string[];
  version: number;
}
```

```python
# backend
class Artifact(BaseModel):
    domain: Domain
    spec: str
    spec_hash: str
    content: str
    assumptions: list[str]
    version: int
```

### Attack — a single adversarial probe (must carry checkable evidence)

```jsonc
{
  "id": "atk_7f3",
  "breaker": "boundary",
  "signature": "sha256:...",        // normalized -> dedup key
  "rationale": "n=0 edge case",     // <= ~30 tokens, UI only
  // exactly ONE evidence payload, by domain:
  "test":        { "input": "0", "expected": "0" },          // code
  "computation": { "expr": "fib(10)", "expected": "55" },    // math
  "claimCheck":  { "claim": "JWST launched 2021",
                   "sourceQuery": "JWST launch date" }        // factual
}
```

> **GROUND-TRUTH RULE (non-negotiable).** An Attack with no `test`,
> `computation`, or `claimCheck` is INVALID and dropped at validation. A breaker
> never wins by assertion. This is what keeps the demo objective instead of two
> bots arguing.

### Verdict — a verifier's ruling on one attack

```jsonc
{
  "attackId": "atk_7f3",
  "landed": true,                   // true = the attack broke the artifact
  "actual": "1",                    // what actually happened
  "evidence": "expected 0, got 1"   // human-readable, shown in UI
}
```

---

## 2. Role interfaces (the four frozen contracts)

```
BUILDER   : (spec)                              -> { content, assumptions[] }
            // also handles PATCH: (artifact, landedVerdicts[]) -> content'

BREAKER   : (spec, content, weaknessClass, ledgerDigest) -> Attack[]
            // <= MAX_ATTACKS_PER_BREAKER, novel only, evidence required

VERIFIER  : (artifact, attack) -> Verdict
            // router dispatches: code/math -> PyExec, factual -> NLI

SCORER    : (verdicts[], round) -> { robustness, newBreaks, survived, landed }
```

### Ledger digest (shared swarm memory, read by every breaker)

```jsonc
{
  "tried":     ["sha256:...", "sha256:..."],   // signatures only (token-cheap)
  "survivors": [ /* Attack[] the current version passes */ ],
  "landed":    [ /* Attack[] that broke a prior version */ ]
}
```

---

## 3. Scoring (fixed formula)

```
robustness = sum(survived_i * w_i) / sum(verified_i * w_i)     # 0..1
weights:  spec_gap = 1.5   factual = 1.5   numeric_type = 1.2   boundary = 1.0
```

An attack "survives" when the CURRENT artifact version passes it. A patch flips
prior landed breaks to survived, so the dial climbs as the artifact hardens.

---

## 4. SSE events (orchestrator -> frontend)

One event per FSM transition. Payloads stay small.

```
STATE      { state, round }
BUILDER    { version, contentPreview }
ATTACK     { attack }                 // streamed per attack as it is produced
VERDICT    { verdict }                // streamed per verification
SCORE      { robustness, newBreaks, survived, landed, round }
ROUND_END  { round, newBreaks }
DONE       { reason: "converged" | "max_rounds", robustness }
ERROR      { where, message }         // never crash the stream
```

---

## 5. Model Gateway interface (keys + rotation live here only)

```
gateway.call(role, messages, { maxTokens, temp, seed }) -> { text, usage }

role -> ordered endpoint list, each with its own key pool:
  builder : [ { provider: "groq",     model: GROQ_BUILDER_MODEL,    keys: [...] } ]
  breaker : [ { provider: "aistudio", model: AISTUDIO_BREAKER_MODEL, keys: [...] } ]

rotation:
  - rotate ONLY on 429 / quota / 5xx / timeout  (never on 4xx: that is a bug)
  - on rotate: mark key cooldownUntil, retry same call on next healthy key
  - breaker fan-out: assign the 4 concurrent calls least-inflight across keys
  - all keys cooling -> surface a clean "rate-limited, retrying" state
```

No module except the Gateway knows a key exists.
