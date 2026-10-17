import type { FsmState, VerdictColor } from "./view-model";

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

export function formatRobustness(value: number | null): string {
  if (value === null) return "—";
  return value.toFixed(2);
}
