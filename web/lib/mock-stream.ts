/**
 * The client-side mock. Emits a scripted CONTRACTS §4 sequence so the whole arena
 * animates end-to-end with no backend (TR-24 acceptance). It yields typed SseEvents
 * directly — it deliberately skips the wire layer (that is covered by sse-parser);
 * both paths converge on the same event type the reducer consumes.
 *
 * One planted-flaw run per domain, each the same arc: a flawed v1 draws attacks,
 * some land, the Builder patches, re-verification flips every break to survived,
 * and the run converges with the dial climbing to 0.95.
 *   - code    → a Fibonacci function that mishandles n=0 / negatives / an O(1) claim.
 *   - math    → a sum closed-form that is off by one (n·(n−1)/2 instead of n·(n+1)/2).
 *   - factual → a JWST answer with a contradicted orbit claim and an unsupported one;
 *               its verdicts carry the structured NLI label so the TR-25 amber-vs-red
 *               grammar is exact (SUPPORTED=green · UNSUPPORTED=amber · CONTRADICTED=red).
 */

import type { Domain } from "./view-model";
import type { RunRequest, SseEvent } from "./types";

interface Step {
  wait: number;
  event: SseEvent;
}

// ── code (Fibonacci) ─────────────────────────────────────────────────────────

const CODE_V1 = [
  "def fib(n):",
  '    """Return the nth Fibonacci number in O(1)."""',
  "    a, b = 1, 1",
  "    for _ in range(n):",
  "        a, b = b, a + b",
  "    return a",
].join("\n");

const CODE_V2 = [
  "def fib(n):",
  '    """Return the nth Fibonacci number for n >= 0."""',
  "    if n < 0:",
  '        raise ValueError("n >= 0")',
  "    a, b = 0, 1",
  "    for _ in range(n):",
  "        a, b = b, a + b",
  "    return a",
].join("\n");

const CODE_SCRIPT: Step[] = [
  // ── Round 1 — draft the (flawed) answer ──────────────────────────────────
  { wait: 300, event: { type: "STATE", state: "GENERATE", round: 1 } },
  { wait: 750, event: { type: "BUILDER", version: 1, contentPreview: CODE_V1 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 1 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "atk_7f3",
        breaker: "boundary",
        signature: "sha256:7f3",
        rationale: "n=0 edge case",
        test: { input: "0", expected: "0" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "atk_9a1",
        breaker: "numeric_type",
        signature: "sha256:9a1",
        rationale: "large n, no overflow",
        test: { input: "90", expected: "2880067194370816120" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "atk_c22",
        breaker: "spec_gap",
        signature: "sha256:c22",
        rationale: "negative input unspecified",
        test: { input: "-1", expected: "ValueError" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "atk_e05",
        breaker: "factual",
        signature: "sha256:e05",
        rationale: "docstring claims O(1)",
        claimCheck: {
          claim: "fib runs in O(1)",
          sourceQuery: "fibonacci iterative time complexity",
        },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 1 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: { attackId: "atk_7f3", landed: true, actual: "1", evidence: "expected 0, got 1" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "atk_9a1",
        landed: false,
        actual: "2880067194370816120",
        evidence: "matched expected (Python bigint)",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "atk_c22",
        landed: true,
        actual: "1",
        evidence: "expected ValueError, got 1",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "atk_e05",
        landed: true,
        actual: "no source",
        evidence: "UNSUPPORTED — no source for an O(1) claim",
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 1 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.33, newBreaks: 3, survived: 1, landed: 3, round: 1 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 1, newBreaks: 3 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 1 } },

  // ── Round 2 — patch, re-verify, converge ─────────────────────────────────
  { wait: 350, event: { type: "STATE", state: "PATCH", round: 2 } },
  { wait: 800, event: { type: "BUILDER", version: 2, contentPreview: CODE_V2 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 2 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "atk_f71",
        breaker: "boundary",
        signature: "sha256:f71",
        rationale: "n=1 base case",
        test: { input: "1", expected: "1" },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 2 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: { attackId: "atk_7f3", landed: false, actual: "0", evidence: "fib(0) = 0, passes" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "atk_c22",
        landed: false,
        actual: "ValueError",
        evidence: "raises ValueError as specified",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "atk_e05",
        landed: false,
        actual: "claim removed",
        evidence: "SUPPORTED — unverifiable O(1) claim removed",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: { attackId: "atk_f71", landed: false, actual: "1", evidence: "fib(1) = 1, passes" },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 2 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.95, newBreaks: 0, survived: 5, landed: 0, round: 2 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 2, newBreaks: 0 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 2 } },
  { wait: 450, event: { type: "DONE", reason: "converged", robustness: 0.95 } },
];

// ── math (closed-form sum) ─────────────────────────────────────────────────────

const MATH_V1 = [
  "Claim. For a positive integer n,",
  "    S(n) = 1 + 2 + ... + n = n·(n − 1) / 2.",
  "",
  "Proof sketch. Pair the first and last terms, the second and",
  "second-last, and so on; each pair sums to the same total, a",
  "trick attributed to Gauss.",
].join("\n");

const MATH_V2 = [
  "Claim. For a non-negative integer n,",
  "    S(n) = 1 + 2 + ... + n = n·(n + 1) / 2.",
  "",
  "Proof. Pair i with (n + 1 − i): there are n such terms and",
  "each pair sums to (n + 1), so 2·S(n) = n·(n + 1), hence",
  "S(n) = n·(n + 1) / 2. For n = 0 the empty sum is 0.",
].join("\n");

const MATH_SCRIPT: Step[] = [
  { wait: 300, event: { type: "STATE", state: "GENERATE", round: 1 } },
  { wait: 750, event: { type: "BUILDER", version: 1, contentPreview: MATH_V1 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 1 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "mth_n1",
        breaker: "boundary",
        signature: "sha256:m01",
        rationale: "smallest case n=1",
        computation: { expr: "S(1)", expected: "1" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "mth_n10",
        breaker: "numeric_type",
        signature: "sha256:m10",
        rationale: "mid case n=10",
        computation: { expr: "S(10)", expected: "55" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "mth_n100",
        breaker: "spec_gap",
        signature: "sha256:m99",
        rationale: "large case n=100",
        computation: { expr: "S(100)", expected: "5050" },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "mth_gauss",
        breaker: "factual",
        signature: "sha256:mga",
        rationale: "attribution of the pairing trick",
        claimCheck: {
          claim: "Pairing trick attributed to Gauss",
          sourceQuery: "Gauss sum 1 to 100 schoolboy story",
        },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 1 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: { attackId: "mth_n1", landed: true, actual: "0", evidence: "expected 1, got 0" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: { attackId: "mth_n10", landed: true, actual: "45", evidence: "expected 55, got 45" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "mth_n100",
        landed: true,
        actual: "4950",
        evidence: "expected 5050, got 4950",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "mth_gauss",
        landed: false,
        label: "SUPPORTED",
        actual: "well-attested",
        evidence: "SUPPORTED — the schoolboy attribution is widely documented",
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 1 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.25, newBreaks: 3, survived: 1, landed: 3, round: 1 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 1, newBreaks: 3 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 1 } },

  { wait: 350, event: { type: "STATE", state: "PATCH", round: 2 } },
  { wait: 800, event: { type: "BUILDER", version: 2, contentPreview: MATH_V2 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 2 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "mth_n0",
        breaker: "boundary",
        signature: "sha256:m00",
        rationale: "empty sum n=0",
        computation: { expr: "S(0)", expected: "0" },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 2 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: { attackId: "mth_n1", landed: false, actual: "1", evidence: "S(1) = 1, passes" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: { attackId: "mth_n10", landed: false, actual: "55", evidence: "S(10) = 55, passes" },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "mth_n100",
        landed: false,
        actual: "5050",
        evidence: "S(100) = 5050, passes",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: { attackId: "mth_n0", landed: false, actual: "0", evidence: "S(0) = 0, passes" },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 2 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.95, newBreaks: 0, survived: 5, landed: 0, round: 2 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 2, newBreaks: 0 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 2 } },
  { wait: 450, event: { type: "DONE", reason: "converged", robustness: 0.95 } },
];

// ── factual (JWST answer) ──────────────────────────────────────────────────────

const FACTUAL_V1 = [
  "The James Webb Space Telescope launched on 25 December 2021.",
  "Its segmented primary mirror spans 6.5 meters across.",
  "It orbits Earth at an altitude of about 550 km, like Hubble.",
  "It can already see the very first stars that formed after the Big Bang.",
].join("\n");

const FACTUAL_V2 = [
  "The James Webb Space Telescope launched on 25 December 2021.",
  "Its segmented primary mirror spans 6.5 meters across.",
  "It orbits the Sun–Earth L2 point, about 1.5 million km from Earth.",
  "It observes some of the earliest galaxies formed after the Big Bang.",
].join("\n");

const FACTUAL_SCRIPT: Step[] = [
  { wait: 300, event: { type: "STATE", state: "GENERATE", round: 1 } },
  { wait: 750, event: { type: "BUILDER", version: 1, contentPreview: FACTUAL_V1 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 1 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "fct_lau",
        breaker: "boundary",
        signature: "sha256:fla",
        rationale: "launch date claim",
        claimCheck: {
          claim: "Launched 25 December 2021",
          sourceQuery: "JWST launch date",
        },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "fct_mir",
        breaker: "numeric_type",
        signature: "sha256:fmi",
        rationale: "mirror diameter claim",
        claimCheck: {
          claim: "Primary mirror is 6.5 m across",
          sourceQuery: "JWST primary mirror diameter",
        },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "fct_orb",
        breaker: "factual",
        signature: "sha256:for",
        rationale: "orbit claim",
        claimCheck: {
          claim: "Orbits Earth at ~550 km, like Hubble",
          sourceQuery: "JWST orbit L2 Lagrange point distance",
        },
      },
    },
  },
  {
    wait: 420,
    event: {
      type: "ATTACK",
      attack: {
        id: "fct_stars",
        breaker: "spec_gap",
        signature: "sha256:fst",
        rationale: "first-stars claim",
        claimCheck: {
          claim: "Already sees the very first stars",
          sourceQuery: "JWST first Population III stars observed",
        },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 1 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_lau",
        landed: false,
        label: "SUPPORTED",
        actual: "2021-12-25",
        evidence: "SUPPORTED — matches the NASA launch record",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_mir",
        landed: false,
        label: "SUPPORTED",
        actual: "6.5 m",
        evidence: "SUPPORTED — matches the NASA mirror spec",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_orb",
        landed: true,
        label: "CONTRADICTED",
        actual: "Sun–Earth L2, ~1.5M km",
        evidence: "CONTRADICTED — JWST orbits L2, not low Earth orbit",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_stars",
        landed: true,
        label: "UNSUPPORTED",
        actual: "no source",
        evidence: "UNSUPPORTED — no source confirms observing the first stars",
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 1 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.42, newBreaks: 2, survived: 2, landed: 2, round: 1 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 1, newBreaks: 2 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 1 } },

  { wait: 350, event: { type: "STATE", state: "PATCH", round: 2 } },
  { wait: 800, event: { type: "BUILDER", version: 2, contentPreview: FACTUAL_V2 } },
  { wait: 300, event: { type: "STATE", state: "FANOUT", round: 2 } },
  {
    wait: 450,
    event: {
      type: "ATTACK",
      attack: {
        id: "fct_l2",
        breaker: "numeric_type",
        signature: "sha256:fl2",
        rationale: "L2 distance claim",
        claimCheck: {
          claim: "Sits at L2, ~1.5 million km",
          sourceQuery: "JWST L2 distance kilometers",
        },
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "VERIFY", round: 2 } },
  {
    wait: 560,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_orb",
        landed: false,
        label: "SUPPORTED",
        actual: "Sun–Earth L2",
        evidence: "SUPPORTED — orbit corrected to the L2 point",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_stars",
        landed: false,
        label: "SUPPORTED",
        actual: "earliest galaxies",
        evidence: "SUPPORTED — claim scoped to the earliest galaxies",
      },
    },
  },
  {
    wait: 520,
    event: {
      type: "VERDICT",
      verdict: {
        attackId: "fct_l2",
        landed: false,
        label: "SUPPORTED",
        actual: "~1.5M km",
        evidence: "SUPPORTED — L2 distance confirmed",
      },
    },
  },
  { wait: 400, event: { type: "STATE", state: "SCORE", round: 2 } },
  {
    wait: 500,
    event: { type: "SCORE", robustness: 0.95, newBreaks: 0, survived: 5, landed: 0, round: 2 },
  },
  { wait: 350, event: { type: "ROUND_END", round: 2, newBreaks: 0 } },
  { wait: 300, event: { type: "STATE", state: "DECIDE", round: 2 } },
  { wait: 450, event: { type: "DONE", reason: "converged", robustness: 0.95 } },
];

// ── per-domain registry ────────────────────────────────────────────────────────

interface MockRun {
  run: RunRequest;
  script: Step[];
}

const RUNS: Record<Domain, MockRun> = {
  code: {
    run: { domain: "code", query: "Return the nth Fibonacci number, n >= 0." },
    script: CODE_SCRIPT,
  },
  math: {
    run: { domain: "math", query: "Give a closed form for 1 + 2 + ... + n and justify it." },
    script: MATH_SCRIPT,
  },
  factual: {
    run: {
      domain: "factual",
      query: "When did the James Webb telescope launch, and how wide is its mirror?",
    },
    script: FACTUAL_SCRIPT,
  },
};

/** The default auto-play run (code). Kept for the ArenaRunner mount + existing tests. */
export const MOCK_RUN: RunRequest = RUNS.code.run;

/** The sample request for a given domain — what the DomainToggle replays in demo mode. */
export function mockRunFor(domain: Domain): RunRequest {
  return (RUNS[domain] ?? RUNS.code).run;
}

/** The ordered events for a domain, independent of timing — handy for tests and replay. */
export function mockEventsFor(domain: Domain): readonly SseEvent[] {
  return (RUNS[domain] ?? RUNS.code).script.map((s) => s.event);
}

/** The code run's events (back-compat default). */
export const MOCK_EVENTS: readonly SseEvent[] = mockEventsFor("code");

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve();
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

/**
 * Emit the scripted run for `req.domain` with lifelike pacing. `speed` > 1
 * fast-forwards (useful in tests / rehearsal). Honors the abort signal between
 * every step. Unknown domains fall back to the code run.
 */
export async function* mockCrucibleStream(
  req: RunRequest,
  signal: AbortSignal,
  opts: { speed?: number } = {},
): AsyncGenerator<SseEvent> {
  const speed = opts.speed ?? 1;
  const { script } = RUNS[req.domain] ?? RUNS.code;
  for (const step of script) {
    await sleep(step.wait / speed, signal);
    if (signal.aborted) return;
    yield step.event;
  }
}
