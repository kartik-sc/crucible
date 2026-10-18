"use client";

import { motion } from "framer-motion";
import type { ArenaState } from "@/lib/view-model";
import { tallyOf } from "@/lib/tally";

/** Round-by-round scorecard: who took each round. The phase rail shows the live beat. */
export function RoundTimeline({ state }: { state: ArenaState }) {
  const { round, fsm } = state;
  const running = fsm !== "done" && fsm !== "idle" && fsm !== "error";
  const { rounds } = tallyOf(state);

  return (
    <div className="px-1 py-4">
      <ol className="flex flex-wrap items-stretch gap-2" aria-label="Rounds">
        {rounds.map((r) => {
          const isCurrent = r.round === round && running && r.winner === null;
          const tone =
            r.winner === "swarm"
              ? "border-swarm/40 bg-swarm/[0.08]"
              : r.winner === "builder"
                ? "border-builder/40 bg-builder/[0.07]"
                : isCurrent
                  ? "border-accent/50 bg-accent/[0.06]"
                  : "border-hairline";
          return (
            <motion.li
              key={r.round}
              layout
              className={`relative flex min-w-[7.5rem] flex-col rounded-lg border px-3 py-2 transition-colors duration-500 ${tone}`}
            >
              <span className="flex items-center justify-between gap-3 font-mono text-[11px] text-bone-faint">
                R{r.round}
                {isCurrent && (
                  <span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
                )}
              </span>
              <span className="mt-0.5 font-sans text-[13px] text-bone">
                {r.winner === "swarm" ? (
                  <>
                    <span className="text-swarm">Swarm</span> +{r.newBreaks}
                  </>
                ) : r.winner === "builder" ? (
                  <span className="text-builder">Builder clean</span>
                ) : isCurrent ? (
                  <span className="text-bone-dim">In the ring</span>
                ) : (
                  <span className="text-bone-faint">—</span>
                )}
              </span>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}
