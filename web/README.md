# web — CRUCIBLE frontend (Next.js · Vercel)

The arena the judges see: a split-screen **builder | swarm**, an animated
robustness dial, a round timeline, and the live attack/verdict stream. Owner C
(M3). Built against a client-side mock, it goes live by pointing one env var at the
Render backend — no code change.

## Run

```bash
npm install
npm run dev        # http://localhost:3000 — auto-plays the mock run
```

| Script | Does |
|---|---|
| `npm run dev` | dev server |
| `npm run build` / `start` | production build / serve |
| `npm run typecheck` | `tsc --noEmit` (strict) |
| `npm run lint` | ESLint (next/core-web-vitals) |
| `npm test` | Vitest |

## Data source (mock ↔ live)

One env var switches the whole app; no component knows which is active.

```bash
# .env.local  (copy from .env.example)
# unset            → client-side mock (demo default)
NEXT_PUBLIC_API_URL=https://crucible-api.onrender.com   # → live POST /run
```

The browser calls the Render backend's `/run` **directly** (never through a Next.js
API route — Vercel's function timeouts would cut the stream). `/run` is a POST with
a JSON body, so the client uses `fetch` + a `ReadableStream` parser, not
`EventSource`.

## Architecture

The **event log is the source of truth**. Everything flows one way:

```
stream-source ─▶ SseEvent ─▶ reduce() ─▶ ArenaState ─▶ components
  (mock | fetch)              (pure)                     (read-only)
```

- `lib/types.ts` — the wire contract (CONTRACTS §1 + §4).
- `lib/view-model.ts` — `ArenaState`, the read model components bind to.
- `lib/reducer.ts` — the one pure `(state, event) => state`. No component parses events.
- `lib/mock-stream.ts` · `lib/sse-parser.ts` · `lib/stream-source.ts` — the two
  stream sources behind one `CrucibleStream` type.
- `hooks/useCrucibleStream.ts` — folds the stream into state.
- `components/` — presentational; `ArenaRunner` wires the hook to `Arena`.

## Color grammar (TR-25)

green = survived · amber = unsupported · red = contradicted / struck.

## Open contract asks

Frozen-file changes needed from M1/backend are tracked in
[`docs/contract-asks.md`](./docs/contract-asks.md). The frontend is forward-compatible
with all of them, so nothing is blocked today.
