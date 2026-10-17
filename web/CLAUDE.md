# web/CLAUDE.md — CRUCIBLE frontend (M3 / Owner C)

## Scope
Edit only files under web/, plus README.md, vercel.json, and docs/demo.md.
Never edit server/, CONTRACTS.md, .env.example, or any other frozen file.
If one needs to change, STOP and tell M3 so they can coordinate with the team.

## Stack
Next.js App Router · TypeScript strict · Tailwind · Framer Motion (animation) ·
Vitest (tests). No other dependency without asking M3 first.

## Architecture
The event log is the source of truth. One reducer turns SSE events into state.
Components only read state — none of them parse events. Small modules, one job each.

## Colors (TR-25)
green = survived · amber = unsupported · red = contradicted or struck.

## Data source
An env flag switches between the client-side mock and the real /run. No component
knows which one is active — both feed the same reducer through the same parser.

## Streaming
Never route the stream through a Next.js API route (Vercel time limits cut it off).
The browser calls the Render backend directly via fetch + a ReadableStream parser
(POST /run cannot use EventSource — it is a POST with a JSON body).

## Definition of done (every step)
typecheck + lint + tests pass → small, focused change on branch c/* → STOP and
report to M3 (what was built, files changed, how to verify, open issues).
Do NOT commit and do NOT add Co-Authored-By/attribution lines — M3 commits manually.
Never start the next step on your own.
