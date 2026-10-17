# CONTRIBUTING

Small, reviewable PRs. We work on branches and merge via PR — this keeps the
history clean, shows all three contributors (a judging signal), and lets the
**ShipWright AI** code-review bot review real PRs (which also feeds the
ShipWright leaderboard challenge).

## Workflow

1. Branch from `main`: `git checkout -b <owner>/<short-topic>`
   e.g. `a/loop-engine`, `b/breaker-boundary`, `c/arena-dial`.
2. Keep PRs small and focused — one module or one feature.
3. Open a PR into `main`. Fill the checklist below.
4. **ShipWright** will comment. Its suggestions are recommendations: apply good
   ones, and reply explaining why any inapplicable suggestion is skipped (do not
   make a risky change just to satisfy a bot).
5. One teammate reviews + merges. Do not merge your own PR unreviewed when
   avoidable.

## Branch ownership (avoid collisions)

- `a/*` — orchestrator, gateway, ledger, SSE
- `b/*` — breakers, builder, verifiers, scorer
- `c/*` — web / UI / demo

Touch another owner's area only via a PR they review.

## Commit messages

Conventional style: `feat(gateway): key rotation on 429`, `fix(breaker):
drop attacks without evidence`, `docs(readme): problem-first intro`.

## PR checklist

- [ ] Matches CONTRACTS.md (no silent field changes)
- [ ] No secrets committed (`.env` stays local)
- [ ] Runs locally / doesn't break the live deploy
- [ ] Small enough to review in a few minutes
- [ ] ShipWright comments addressed or answered

## Definition of done for the MUST-HAVE tier

builder -> 1 breaker -> verifier -> patch -> score renders one full round in the
arena, on the deployed URL.
