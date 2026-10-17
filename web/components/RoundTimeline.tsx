"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { ArenaState } from "@/lib/view-model";
import { FSM_LABEL } from "@/lib/ui";
import { EASE_OUT } from "@/lib/motion";

export function RoundTimeline({ state }: { state: ArenaState }) {
  const { round, maxRounds, rounds, fsm } = state;
  const dots = Array.from({ length: maxRounds }, (_, i) => i + 1);
  const breaksByRound = new Map(rounds.map((r) => [r.round, r.newBreaks]));
  const running = fsm !== "done" && fsm !== "idle" && fsm !== "error";

  return (
    <div className="flex items-center justify-between gap-6 px-6 py-4">
      <div className="flex items-center gap-4">
        {dots.map((n) => {
          const isCurrent = n === round && running;
          const isDone = n < round || (n === round && !running && fsm === "done");
          return (
            <div key={n} className="flex items-center gap-2">
              <motion.span
                aria-hidden
                animate={{ scale: isCurrent ? 1.15 : 1 }}
                transition={{ duration: 0.3, ease: EASE_OUT }}
                className={[
                  "h-2.5 w-2.5 rounded-full transition-colors duration-300",
                  isCurrent
                    ? "bg-accent ring-4 ring-accent/15"
                    : isDone
                      ? "bg-bone"
                      : "border border-hairline bg-transparent",
                ].join(" ")}
              />
              <span className="font-mono text-[11px] text-bone-faint">
                R{n}
                {breaksByRound.has(n) && (
                  <span className="ml-1 text-struck">+{breaksByRound.get(n)}</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        {running && <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-accent" />}
        <AnimatePresence mode="wait">
          <motion.span
            key={fsm}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
            className="font-sans text-[11px] uppercase tracking-label text-bone-dim"
          >
            {FSM_LABEL[fsm]}
          </motion.span>
        </AnimatePresence>
      </div>
    </div>
  );
}
