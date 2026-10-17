/**
 * The one reducer. `(ArenaState, SseEvent) => ArenaState`, pure and total — every
 * event returns a new state, unknown shapes are ignored rather than thrown. This
 * is the ONLY module that reads raw events; every component binds to the result.
 *
 * The same reducer consumes the client-side mock and the live /run stream, so if
 * it is correct here, it is correct in production (web/CLAUDE.md).
 */

import type {
  ArenaState,
  AttackView,
  Domain,
  EvidenceKind,
  FsmState,
  VerdictColor,
} from "./view-model";
import type { Attack, SseEvent, Verdict } from "./types";
import { attackKind } from "./types";

const DEFAULT_MAX_ROUNDS = 4;

export function createInitialState(init: {
  domain: Domain;
  query: string;
  maxRounds?: number;
}): ArenaState {
  return {
    domain: init.domain,
    query: init.query,
    fsm: "idle",
    round: 0,
    maxRounds: init.maxRounds ?? DEFAULT_MAX_ROUNDS,
    builder: null,
    attacks: [],
    robustness: null,
    robustnessHistory: [],
    rounds: [],
    done: null,
    error: null,
  };
}

const FSM_FROM_WIRE: Record<string, FsmState> = {
  GENERATE: "generate",
  FANOUT: "fanout",
  VERIFY: "verify",
  SCORE: "score",
  DECIDE: "decide",
  PATCH: "patch",
  DONE: "done",
};

function toFsm(wire: string, fallback: FsmState): FsmState {
  return FSM_FROM_WIRE[wire.toUpperCase()] ?? fallback;
}

function evidenceLabel(attack: Attack): string {
  if ("test" in attack) return `${attack.test.input} → ${attack.test.expected}`;
  if ("computation" in attack)
    return `${attack.computation.expr} = ${attack.computation.expected}`;
  return attack.claimCheck.claim;
}

function toAttackView(attack: Attack): AttackView {
  return {
    id: attack.id,
    breaker: attack.breaker,
    kind: attackKind(attack),
    rationale: attack.rationale,
    evidenceLabel: evidenceLabel(attack),
    verdict: "pending",
  };
}

/**
 * Resolve the TR-25 color from a verdict. The contract's Verdict has no structured
 * NLI label, so an UNSUPPORTED (amber) factual result is distinguished from a
 * CONTRADICTED (red) one by sniffing the evidence string.
 *
 * TODO(contract): propose a structured `Verdict.label?` so color is not derived
 * from free text (open issue #5 — raise with M1).
 */
function verdictColor(kind: EvidenceKind, verdict: Verdict): VerdictColor {
  if (!verdict.landed) return "survived";
  if (kind === "claimCheck" && /unsupported/i.test(verdict.evidence)) {
    return "unsupported";
  }
  return "struck";
}

function upsertRound(
  rounds: ArenaState["rounds"],
  round: number,
  newBreaks: number,
): ArenaState["rounds"] {
  const seen = rounds.some((r) => r.round === round);
  if (seen) return rounds.map((r) => (r.round === round ? { round, newBreaks } : r));
  return [...rounds, { round, newBreaks }];
}

export function reduce(state: ArenaState, event: SseEvent): ArenaState {
  switch (event.type) {
    case "STATE":
      return { ...state, fsm: toFsm(event.state, state.fsm), round: event.round };

    case "BUILDER":
      return {
        ...state,
        builder: { version: event.version, contentPreview: event.contentPreview },
      };

    case "ATTACK": {
      // Dedup by id: a re-emitted attack keeps its existing verdict.
      if (state.attacks.some((a) => a.id === event.attack.id)) return state;
      return { ...state, attacks: [...state.attacks, toAttackView(event.attack)] };
    }

    case "VERDICT": {
      // Join by attackId. A later verdict for the same attack (after a patch)
      // updates it in place — this is what flips a prior struck → survived.
      let matched = false;
      const attacks = state.attacks.map((a) => {
        if (a.id !== event.verdict.attackId) return a;
        matched = true;
        return {
          ...a,
          verdict: verdictColor(a.kind, event.verdict),
          actual: event.verdict.actual,
          evidence: event.verdict.evidence,
        };
      });
      return matched ? { ...state, attacks } : state;
    }

    case "SCORE":
      return {
        ...state,
        round: event.round,
        robustness: event.robustness,
        robustnessHistory: [...state.robustnessHistory, event.robustness],
      };

    case "ROUND_END":
      return {
        ...state,
        round: event.round,
        rounds: upsertRound(state.rounds, event.round, event.newBreaks),
      };

    case "DONE":
      return {
        ...state,
        fsm: "done",
        robustness: event.robustness,
        done: { reason: event.reason, robustness: event.robustness },
      };

    case "ERROR":
      // Freeze the last good version; only surface the error (TR-6, NFR-4).
      return {
        ...state,
        fsm: "error",
        error: { where: event.where, message: event.message },
      };

    default:
      return state;
  }
}

/** Fold an entire event log into state — handy for tests and replay. */
export function reduceAll(initial: ArenaState, events: readonly SseEvent[]): ArenaState {
  return events.reduce(reduce, initial);
}
