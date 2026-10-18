"use client";

import { useEffect, useRef, useState } from "react";
import type { ArenaState, VerdictColor } from "@/lib/view-model";

/**
 * Turns read-model changes into one-shot "moments" the UI can react to (a strike
 * landing, a patch arriving, the dial climbing). It only diffs successive
 * ArenaStates — it never sees an event, so the reducer stays the single source.
 *
 * Each moment is a counter: components key animations off it, and effects fire
 * once per increment.
 */
export interface ArenaMoments {
  /** increments every time an attack's verdict becomes "struck". */
  strike: number;
  /** increments whenever any attack receives a (new) settled verdict. */
  verdict: number;
  /** id of the attack that was struck most recently. */
  struckId: string | null;
  /** increments when the Builder publishes a new version above v1. */
  patch: number;
  /** increments when robustness rises. */
  climb: number;
  /** the Builder's previous version content, for the v(n-1) → v(n) diff. */
  previousContent: string | null;
}

const INITIAL: ArenaMoments = {
  strike: 0,
  verdict: 0,
  struckId: null,
  patch: 0,
  climb: 0,
  previousContent: null,
};

export function useArenaMoments(state: ArenaState): ArenaMoments {
  const [moments, setMoments] = useState<ArenaMoments>(INITIAL);
  const verdicts = useRef(new Map<string, VerdictColor>());
  const builder = useRef<{ version: number; content: string } | null>(null);
  const robustness = useRef<number | null>(null);

  useEffect(() => {
    const prevVerdicts = verdicts.current;

    // A fresh run (no builder, no attacks) wipes the slate.
    if (state.builder === null && state.attacks.length === 0) {
      verdicts.current = new Map();
      builder.current = null;
      robustness.current = null;
      setMoments(INITIAL);
      return;
    }

    let struckId: string | null = null;
    let ruled = false;
    for (const a of state.attacks) {
      const before = prevVerdicts.get(a.id);
      if (a.verdict === "struck" && before !== "struck") struckId = a.id;
      if (a.verdict !== "pending" && before !== a.verdict) ruled = true;
    }
    verdicts.current = new Map(state.attacks.map((a) => [a.id, a.verdict]));

    let patched = false;
    let previousContent: string | null | undefined;
    const b = state.builder;
    if (b && builder.current?.version !== b.version) {
      if (builder.current && b.version > builder.current.version) {
        previousContent = builder.current.content;
        patched = true;
      } else {
        previousContent = null; // v1 or a restart: nothing to diff against
      }
      builder.current = { version: b.version, content: b.contentPreview };
    }

    const climbed =
      state.robustness !== null &&
      robustness.current !== null &&
      state.robustness > robustness.current;
    robustness.current = state.robustness;

    if (struckId === null && !ruled && !patched && !climbed && previousContent === undefined) return;
    setMoments((m) => ({
      strike: struckId ? m.strike + 1 : m.strike,
      verdict: ruled ? m.verdict + 1 : m.verdict,
      struckId: struckId ?? m.struckId,
      patch: patched ? m.patch + 1 : m.patch,
      climb: climbed ? m.climb + 1 : m.climb,
      previousContent: previousContent === undefined ? m.previousContent : previousContent,
    }));
  }, [state.attacks, state.builder, state.robustness]);

  return moments;
}
