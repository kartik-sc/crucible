/**
 * The read model the arena renders. Components bind to ArenaState and nothing
 * else — they never see a raw SSE event. Step 2's reducer produces exactly this
 * shape from the event log, so this file is the contract between stream and UI.
 */

import type { DoneReason } from "./types";

export type Domain = "code" | "factual" | "math";

export type WeaknessClass = "boundary" | "numeric_type" | "spec_gap" | "factual";

/** Which evidence payload an attack carries (one-of, per CONTRACTS §1). */
export type EvidenceKind = "test" | "computation" | "claimCheck";

/** FSM transitions carried by the STATE event (TR-4). */
export type FsmState =
  | "idle"
  | "generate"
  | "fanout"
  | "verify"
  | "score"
  | "decide"
  | "patch"
  | "done"
  | "error";

/**
 * The TR-25 color grammar, as a resolved view concern:
 * survived (green) · unsupported (amber) · struck (red) · pending (awaiting verdict).
 */
export type VerdictColor = "survived" | "unsupported" | "struck" | "pending";

export interface AttackView {
  id: string;
  breaker: WeaknessClass;
  kind: EvidenceKind;
  rationale: string;
  /** short human label of the probe, e.g. "fib(0) → 0" or "JWST launched 2021". */
  evidenceLabel: string;
  verdict: VerdictColor;
  /** what actually happened, from the Verdict (once settled). */
  actual?: string;
  /** human-readable verdict evidence string. */
  evidence?: string;
}

export interface BuilderView {
  version: number;
  contentPreview: string;
}

export interface RoundView {
  round: number;
  newBreaks: number;
}

export interface ArenaState {
  domain: Domain;
  query: string;
  fsm: FsmState;
  round: number;
  maxRounds: number;
  builder: BuilderView | null;
  attacks: AttackView[];
  robustness: number | null;
  robustnessHistory: number[];
  rounds: RoundView[];
  done: { reason: DoneReason; robustness: number } | null;
  error: { where: string; message: string; fatal: boolean } | null;
}

export const WEAKNESS_LABELS: Record<WeaknessClass, string> = {
  boundary: "Boundary",
  numeric_type: "Numeric / type",
  spec_gap: "Spec gap",
  factual: "Factual",
};

export const DOMAINS: readonly Domain[] = ["code", "factual", "math"] as const;
