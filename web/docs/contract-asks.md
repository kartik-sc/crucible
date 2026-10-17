# Contract asks — frontend → M1 / backend

Six issues the frontend hit. Each lists what M3 already did **inside `web/`** (so
nothing is blocked today) and the exact **frozen-file change** needed from M1 to
close it properly. Frozen files (`CONTRACTS.md`, `.env.example`, `server/`) are not
M3's to edit — these are the asks to coordinate.

---

### #1 — `WEB_PUBLIC_API_URL` never reaches the browser · **needs M1**

Next.js only inlines `NEXT_PUBLIC_`-prefixed env vars into client code, and the SSE
stream is consumed in the browser.

- **Done (web):** the app reads `NEXT_PUBLIC_API_URL`; `web/.env.example` documents
  it; unset → client-side mock, set → live `/run`.
- **Ask:** in root `.env.example`, rename the web var so the two don't diverge:
  ```diff
  - WEB_PUBLIC_API_URL=http://localhost:8000   # set to the Render URL in prod
  + NEXT_PUBLIC_API_URL=http://localhost:8000   # frontend; set to the Render URL in prod
  ```
  Vercel env settings must use `NEXT_PUBLIC_API_URL` too. (TRD §6 names
  `WEB_PUBLIC_API_URL` — update there as well.)

### #2 — CORS "Vercel origin only" blocks previews + needs preflight · **needs M1**

Per-PR Vercel previews get unique origins, and `POST /run` with
`Content-Type: application/json` is not a CORS "simple request" — it triggers an
`OPTIONS` preflight.

- **Done (web):** nothing to change — the client only sends the required headers
  (`Content-Type: application/json`, `Accept: text/event-stream`).
- **Ask:** backend CORS should (a) allow the `*.vercel.app` preview origins (regex
  or allowlist), not a single origin, and (b) answer the `OPTIONS` preflight for
  `/run` with `Access-Control-Allow-Headers: content-type`.

### #3 — SSE wire framing unspecified · **needs M1 sign-off**

CONTRACTS §4 lists event names + payloads but not the on-the-wire framing.

- **Done (web):** `web/lib/sse-parser.ts` implements and documents a proposal:
  ```
  event: ATTACK
  data: {"attack": { ... }}
  <blank line>
  ```
  event name in the `event:` field, JSON payload in `data:` (no `type` inside),
  frames separated by a blank line.
- **Ask:** M1 confirms the orchestrator emits exactly this (standard SSE). If the
  backend instead puts `type` inside the `data` JSON, tell M3 — it's a one-line
  parser change.

### #4 — `STATE.state` values not in the enum list · **resolved defensively**

- **Done (web):** the reducer upper-cases before mapping, so `GENERATE`/`generate`
  both resolve; unknown values keep the current state. No change needed.
- **Ask (optional):** M1 confirms the exact strings
  (`GENERATE FANOUT VERIFY SCORE DECIDE PATCH DONE`) so we can tighten the type.

### #5 — `Verdict` can't distinguish amber vs red · **needs M1 (frontend forward-compatible)**

TR-25 wants amber = UNSUPPORTED, red = CONTRADICTED, but both are `landed:true` and
the NLI label only appears inside the free-text `evidence`.

- **Done (web):** `Verdict.label?: "SUPPORTED"|"CONTRADICTED"|"UNSUPPORTED"` is
  already in the types; the reducer **prefers it** and falls back to sniffing
  `evidence` when absent. Works with or without the field.
- **Ask:** add the optional label to the factual `Verdict` in CONTRACTS §1:
  ```diff
    "attackId": "atk_7f3",
    "landed": true,
    "actual": "1",
  - "evidence": "expected 0, got 1"
  + "evidence": "expected 0, got 1",
  + "label": "UNSUPPORTED"   // factual only; code/math omit it
  ```

### #6 — no home for the final hardened answer · **needs M1 (frontend forward-compatible)**

`DONE` carries `{reason, robustness}` only; FR-6 says "show the hardened answer."

- **Done (web):** the arena treats the latest `BUILDER.contentPreview` as the
  hardened answer and seals the Builder pane ("Hardened") on `DONE`. The reducer
  also honors an optional `DONE.content` if present.
- **Ask (nice-to-have):** add `content` to the `DONE` payload with the full final
  artifact, so the hardened answer isn't limited to a preview.
