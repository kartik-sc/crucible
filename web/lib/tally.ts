/**
 * Fight-card arithmetic, derived purely from ArenaState. Nothing here touches the
 * reducer: it reads the same read model every component reads.
 *
 * Framing: the Builder "wins" an attack it survives; the Swarm "lands" one that is
 * struck. A round goes to the Swarm if any new break landed, else to the Builder.
 */

import type { ArenaState } from "./view-model";

export type Corner = "builder" | "swarm";

export interface RoundResult {
  round: number;
  winner: Corner | null; // null = still being fought
  newBreaks: number;
}

export interface Tally {
  /** attacks currently surviving. */
  held: number;
  /** attacks currently struck. */
  struck: number;
  /** attacks currently unsupported (amber). */
  open: number;
  /** total breaks the Swarm landed across all rounds. */
  landed: number;
  /** breaks that landed and have since been patched (neither struck nor unsupported now). */
  patched: number;
  roundsWonBuilder: number;
  roundsWonSwarm: number;
  rounds: RoundResult[];
}

export function tallyOf(state: ArenaState): Tally {
  const held = state.attacks.filter((a) => a.verdict === "survived").length;
  const struck = state.attacks.filter((a) => a.verdict === "struck").length;
  const open = state.attacks.filter((a) => a.verdict === "unsupported").length;
  // Settled rounds report their breaks at ROUND_END. Mid-round, the strikes on
  // the board are a floor: earlier breaks stay struck until re-verified, so they
  // must not be counted twice.
  const settled = state.rounds.reduce((sum, r) => sum + r.newBreaks, 0);
  const roundSettled = state.rounds.some((r) => r.round === state.round);
  const landed = roundSettled ? settled : Math.max(settled, struck);

  const byRound = new Map(state.rounds.map((r) => [r.round, r.newBreaks]));
  const rounds: RoundResult[] = Array.from({ length: state.maxRounds }, (_, i) => {
    const round = i + 1;
    const breaks = byRound.get(round);
    if (breaks === undefined) return { round, winner: null, newBreaks: 0 };
    return { round, winner: breaks > 0 ? "swarm" : "builder", newBreaks: breaks };
  });

  return {
    held,
    struck,
    open,
    landed,
    // amber (unsupported) breaks are still open, not patched
    patched: Math.max(0, landed - struck - open),
    roundsWonBuilder: rounds.filter((r) => r.winner === "builder").length,
    roundsWonSwarm: rounds.filter((r) => r.winner === "swarm").length,
    rounds,
  };
}

/** Robustness in [0, 1] → a whole percent for display. */
export function toPercent(value: number | null): number {
  return value === null ? 0 : Math.round(Math.max(0, Math.min(1, value)) * 100);
}
