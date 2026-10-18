import {
  BetweenHorizontalStart,
  Binary,
  BookOpen,
  BookOpenCheck,
  Braces,
  FileQuestion,
  Sigma,
  type LucideIcon,
} from "lucide-react";
import type { DoneReason } from "./types";
import type { Domain, FsmState, VerdictColor, WeaknessClass } from "./view-model";

interface VerdictMeta {
  label: string;
  /** Tailwind text color class bound to the TR-25 token. */
  text: string;
  /** whether this is a terminal (settled) verdict. */
  settled: boolean;
}

export const VERDICT_META: Record<VerdictColor, VerdictMeta> = {
  survived: { label: "Survived", text: "text-survived", settled: true },
  unsupported: { label: "Unsupported", text: "text-unsupported", settled: true },
  struck: { label: "Struck", text: "text-struck", settled: true },
  pending: { label: "Pending", text: "text-bone-dim", settled: false },
};

export const FSM_LABEL: Record<FsmState, string> = {
  idle: "Idle",
  generate: "Drafting the answer",
  fanout: "Dispatching the swarm",
  verify: "Weighing the evidence",
  score: "Scoring robustness",
  decide: "Deliberating",
  patch: "Patching the answer",
  done: "Verdict reached",
  error: "Stream interrupted",
};

/** Terminal stop reason shown when a run finishes (DONE.reason). */
export const DONE_REASON_LABEL: Record<DoneReason, string> = {
  converged: "Converged",
  max_rounds: "Max rounds reached",
  gated: "Gated",
};

export function formatRobustness(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(2);
}

// ── icon language ──────────────────────────────────────────────────────────

/** One static glyph per breaker class, so the swarm reads at a glance. */
export const BREAKER_ICON: Record<WeaknessClass, LucideIcon> = {
  boundary: BetweenHorizontalStart,
  numeric_type: Binary,
  spec_gap: FileQuestion,
  factual: BookOpenCheck,
};

export const DOMAIN_ICON: Record<Domain, LucideIcon> = {
  code: Braces,
  factual: BookOpen,
  math: Sigma,
};

// ── the phase rail ─────────────────────────────────────────────────────────

export type Phase = "draft" | "attack" | "verify" | "patch" | "verdict";

export const PHASES: readonly { id: Phase; label: string; hint: string }[] = [
  { id: "draft", label: "Draft", hint: "The Builder writes an answer" },
  { id: "attack", label: "Attack", hint: "The Swarm tries to break it" },
  { id: "verify", label: "Verify", hint: "A verifier runs every attack" },
  { id: "patch", label: "Patch", hint: "The Builder fixes what landed" },
  { id: "verdict", label: "Verdict", hint: "Only what survived ships" },
];

/** Which rail step an FSM state belongs to (null before a run starts). */
export function phaseOf(fsm: FsmState): Phase | null {
  switch (fsm) {
    case "generate":
      return "draft";
    case "fanout":
      return "attack";
    case "verify":
    case "score":
    case "decide":
      return "verify";
    case "patch":
      return "patch";
    case "done":
      return "verdict";
    default:
      return null;
  }
}
