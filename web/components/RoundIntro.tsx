"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ArenaState } from "@/lib/view-model";

const HOLD_MS = 1100;

/** What the previous round means for the one starting, in one line. */
function lineFor(state: ArenaState, round: number): string {
  if (round === 1) return "The Builder drafts. The Swarm attacks.";
  const last = state.rounds.find((r) => r.round === round - 1);
  if (!last || last.newBreaks === 0) return "The answer held. The Swarm goes again.";
  const n = last.newBreaks;
  return `The Swarm landed ${n} ${n === 1 ? "strike" : "strikes"}. The Builder patches.`;
}

/**
 * The fight-game beat between rounds: a title card that slams in over the arena,
 * holds for a second, and gets out of the way. It never blocks input.
 */
export function RoundIntro({ state }: { state: ArenaState }) {
  const [shown, setShown] = useState<{ round: number; line: string } | null>(null);
  const seen = useRef(0);
  const latest = useRef(state);
  latest.current = state;

  useEffect(() => {
    // A new run starts back at a lower round: rearm.
    if (state.round < seen.current) seen.current = 0;
    if (state.round === 0 || state.round <= seen.current) return;
    seen.current = state.round;
    setShown({ round: state.round, line: lineFor(latest.current, state.round) });
    const timer = setTimeout(() => setShown(null), HOLD_MS);
    return () => clearTimeout(timer);
  }, [state.round]);

  return (
    <AnimatePresence>
      {shown && (
        <motion.div
          key={shown.round}
          aria-live="polite"
          className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center bg-ink/55 backdrop-blur-[2px]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.25 } }}
        >
          <motion.div
            className="flex flex-col items-center text-center"
            initial={{ scale: 1.4, opacity: 0, filter: "blur(6px)" }}
            animate={{ scale: 1, opacity: 1, filter: "blur(0px)" }}
            exit={{ scale: 0.96, opacity: 0 }}
            transition={{ type: "spring", stiffness: 520, damping: 26 }}
          >
            <span className="font-serif text-6xl font-semibold tracking-tight text-bone text-glow sm:text-7xl">
              Round {shown.round}
            </span>
            <span className="mt-3 font-serif text-lg italic text-bone-dim">{shown.line}</span>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
