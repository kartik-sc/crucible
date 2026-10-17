/**
 * The client-side mock. Emits a scripted CONTRACTS §4 sequence so the whole arena
 * animates end-to-end with no backend (TR-24 acceptance). It yields typed SseEvents
 * directly — it deliberately skips the wire layer (that is covered by sse-parser);
 * both paths converge on the same event type the reducer consumes.
 *
 * The script is a planted-flaw fib run: v1 fails n=0 / negative / an O(1) claim,
 * the swarm lands the breaks, the Builder patches, re-verification flips every
 * break to survived, and the run converges with the dial climbing 0.33 → 0.95.
 *
 * TODO: per-domain scripts (factual / math). Step 3 ships the code demo only.
 */

import type { RunRequest, SseEvent } from "./types";

export const MOCK_RUN: RunRequest = {
  domain: "code",
  query: "Return the nth Fibonacci number, n >= 0.",
};

const V1 = [
  "def fib(n):",
  '    """Return the nth Fibonacci number in O(1)."""',
  "    a, b = 1, 1",
  "    for _ in range(n):",
  "        a, b = b, a + b",
  "    return a",
].join("\n");

const V2 = [
  "def fib(n):",
  '    """Return the nth Fibonacci number for n >= 0."""',
  "    if n < 0:",
  '        raise ValueError("n >= 0")',
  "    a, b = 0, 1",
  "    for _ in range(n):",
  "        a, b = b, a + b",
  "    return a",
].join("\n");

interface Step {
  wait: number;
  event: SseEvent;
}

const SCRIPT: Step[] = [
  // ── Round 1 — draft the (flawed) answer ──────────────────────────────────
  { wait: 300, event: { type: "STATE", state: "GENERATE", round: 1 } },
  { wait: 750, event: { type: "BUILDER", version: 1, contentPreview: V1 } },
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
  { wait: 800, event: { type: "BUILDER", version: 2, contentPreview: V2 } },
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

/** The ordered events, independent of timing — handy for tests and replay. */
export const MOCK_EVENTS: readonly SseEvent[] = SCRIPT.map((s) => s.event);

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
 * Emit the scripted run with lifelike pacing. `speed` > 1 fast-forwards (useful in
 * tests / rehearsal). Honors the abort signal between every step.
 */
export async function* mockCrucibleStream(
  _req: RunRequest,
  signal: AbortSignal,
  opts: { speed?: number } = {},
): AsyncGenerator<SseEvent> {
  const speed = opts.speed ?? 1;
  for (const step of SCRIPT) {
    await sleep(step.wait / speed, signal);
    if (signal.aborted) return;
    yield step.event;
  }
}
