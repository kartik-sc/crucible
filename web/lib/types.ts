/**
 * Wire types — the TypeScript mirror of CONTRACTS.md §1 (shared types) and §4
 * (SSE events). These are the shapes that come OFF the stream. Nothing here is
 * rendered directly; the reducer turns these into the view-model's ArenaState.
 *
 * Keep this file in sync with CONTRACTS.md. It is the frozen contract; if a field
 * must change, stop and coordinate with the team (see web/CLAUDE.md).
 */

import type { Domain, EvidenceKind, WeaknessClass } from "./view-model";

export type { Domain, WeaknessClass } from "./view-model";

// ── §1 Shared types ────────────────────────────────────────────────────────

export interface Artifact {
  domain: Domain;
  spec: string;
  specHash: string;
  content: string;
  assumptions: string[];
  version: number;
}

export interface TestEvidence {
  input: string;
  expected: string;
}

export interface ComputationEvidence {
  expr: string;
  expected: string;
}

export interface ClaimCheckEvidence {
  claim: string;
  sourceQuery: string;
}

interface AttackBase {
  id: string;
  breaker: WeaknessClass;
  signature: string;
  rationale: string;
}

/** Exactly one evidence payload per attack, by domain (§1 GROUND-TRUTH RULE). */
export interface CodeAttack extends AttackBase {
  test: TestEvidence;
}
export interface MathAttack extends AttackBase {
  computation: ComputationEvidence;
}
export interface FactualAttack extends AttackBase {
  claimCheck: ClaimCheckEvidence;
}

export type Attack = CodeAttack | MathAttack | FactualAttack;

/**
 * NLI entailment labels for factual verdicts (CONTRACTS §0). These are the known
 * constants the color grammar maps directly (see the reducer's `verdictColor`).
 */
export type NliLabel = "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED";

export interface Verdict {
  attackId: string;
  landed: boolean;
  actual: string;
  evidence: string;
  /**
   * Free-text verdict label from the backend. The NLI values (`NliLabel`) drive the
   * amber-vs-red grammar (TR-25); any other value (the live stream also emits e.g.
   * "fail") is opaque and the reducer colors by `landed` instead.
   */
  label?: string;
  /** Verifier confidence in [0, 1], advisory only. */
  confidence?: number;
}

/** POST /run request body (TRD §3). */
export interface RunRequest {
  query: string;
  domain: Domain;
}

/** Why a run stopped (DONE.reason). `gated` = halted by a policy gate. */
export type DoneReason = "converged" | "max_rounds" | "gated";

// ── §4 SSE events ──────────────────────────────────────────────────────────

/**
 * STATE carries the raw FSM transition name. CONTRACTS §0 does not fix its case,
 * so it is typed as a string and normalized in the reducer (open issue #4 —
 * confirm the exact values with M1).
 */
export type SseEvent =
  | { type: "STATE"; state: string; round: number }
  | { type: "BUILDER"; version: number; contentPreview: string }
  | { type: "ATTACK"; attack: Attack }
  | { type: "VERDICT"; verdict: Verdict }
  | {
      type: "SCORE";
      robustness: number;
      newBreaks: number;
      survived: number;
      landed: number;
      round: number;
    }
  | { type: "ROUND_END"; round: number; newBreaks: number }
  | {
      type: "DONE";
      reason: DoneReason;
      robustness: number;
      /**
       * Optional full hardened answer. Not yet in CONTRACTS — proposed to M1
       * (issue #6). When absent, the latest BUILDER contentPreview is treated as
       * the hardened answer; when present, it overrides it.
       */
      content?: string;
    }
  | { type: "ERROR"; where: string; message: string; fatal?: boolean };

export type SseEventType = SseEvent["type"];

export const SSE_EVENT_TYPES: readonly SseEventType[] = [
  "STATE",
  "BUILDER",
  "ATTACK",
  "VERDICT",
  "SCORE",
  "ROUND_END",
  "DONE",
  "ERROR",
] as const;

/** Which one-of evidence payload an attack carries. */
export function attackKind(attack: Attack): EvidenceKind {
  if ("test" in attack) return "test";
  if ("computation" in attack) return "computation";
  return "claimCheck";
}
