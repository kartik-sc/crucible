import type { ArenaState } from "./view-model";

/**
 * A mid-run snapshot used only to build the shell (Step 1). It deliberately
 * exercises every verdict color and a patched builder version so the layout is
 * designed against real density, not an empty state.
 */
export const DEMO_STATE: ArenaState = {
  domain: "code",
  query: "Return the nth Fibonacci number, n >= 0.",
  fsm: "verify",
  round: 2,
  maxRounds: 4,
  builder: {
    version: 2,
    contentPreview:
      "def fib(n):\n    if n < 0:\n        raise ValueError('n >= 0')\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
  },
  attacks: [
    {
      id: "atk_7f3",
      breaker: "boundary",
      kind: "test",
      rationale: "n=0 edge case",
      evidenceLabel: "fib(0) → 0",
      verdict: "struck",
      actual: "1",
      evidence: "expected 0, got 1",
    },
    {
      id: "atk_9a1",
      breaker: "numeric_type",
      kind: "test",
      rationale: "large n overflow",
      evidenceLabel: "fib(90) → 2880067194370816120",
      verdict: "survived",
      actual: "2880067194370816120",
      evidence: "matched expected",
    },
    {
      id: "atk_c22",
      breaker: "spec_gap",
      kind: "test",
      rationale: "negative input unspecified",
      evidenceLabel: "fib(-1) → ValueError",
      verdict: "survived",
      actual: "ValueError",
      evidence: "raises as patched",
    },
    {
      id: "atk_e05",
      breaker: "factual",
      kind: "claimCheck",
      rationale: "docstring claims O(1)",
      evidenceLabel: "claim: runs in O(1)",
      verdict: "unsupported",
      actual: "no source",
      evidence: "UNSUPPORTED — no citation for O(1)",
    },
    {
      id: "atk_f71",
      breaker: "boundary",
      kind: "test",
      rationale: "n=1 base case",
      evidenceLabel: "fib(1) → 1",
      verdict: "pending",
    },
  ],
  robustness: 0.74,
  robustnessHistory: [0.41, 0.6, 0.74],
  rounds: [
    { round: 1, newBreaks: 2 },
    { round: 2, newBreaks: 1 },
  ],
  done: null,
  error: null,
};
