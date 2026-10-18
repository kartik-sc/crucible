"use client";

import { motion } from "framer-motion";
import { PenLine, Swords, Gavel, Wrench, Trophy, type LucideIcon } from "lucide-react";
import type { ArenaState } from "@/lib/view-model";
import { PHASES, phaseOf, type Phase } from "@/lib/ui";
import { tallyOf } from "@/lib/tally";
import { SPRING_SETTLE } from "@/lib/motion";

const ICON: Record<Phase, LucideIcon> = {
  draft: PenLine,
  attack: Swords,
  verify: Gavel,
  patch: Wrench,
  verdict: Trophy,
};

/** Who holds the floor in each phase: Builder green, Swarm red, the verifier in the accent. */
const ACTOR: Record<Phase, { text: string; ring: string; fill: string }> = {
  draft: { text: "text-builder", ring: "border-builder/60 bg-builder/10", fill: "bg-builder" },
  attack: { text: "text-swarm", ring: "border-swarm/60 bg-swarm/10", fill: "bg-swarm" },
  verify: { text: "text-accent", ring: "border-accent/60 bg-accent/10", fill: "bg-accent" },
  patch: { text: "text-builder", ring: "border-builder/60 bg-builder/10", fill: "bg-builder" },
  verdict: { text: "text-survived", ring: "border-survived/60 bg-survived/10", fill: "bg-survived" },
};

/**
 * "You are here" for a viewer seeing the run cold: the five beats of a trial,
 * with the live one lit in its actor's colour. Rounds loop the middle beats,
 * so the round number sits at the head of the rail.
 */
export function PhaseRail({ state }: { state: ArenaState }) {
  const current = phaseOf(state.fsm);
  const index = current ? PHASES.findIndex((p) => p.id === current) : -1;
  const contested = state.done !== null && tallyOf(state).struck > 0;
  const progress = index <= 0 ? 0 : index / (PHASES.length - 1);

  return (
    <nav
      aria-label="Trial progress"
      className="relative flex items-center gap-4 rounded-xl border border-hairline bg-ink-2/50 px-4 py-3 sm:px-6"
    >
      <span className="hidden shrink-0 font-mono text-xs text-bone-faint sm:block">
        {state.round > 0 ? `Round ${state.round}` : "Ready"}
      </span>

      <ol className="relative grid flex-1 grid-cols-5">
        {/* the track and its fill run behind the nodes, centre to centre */}
        <span aria-hidden className="absolute left-[10%] right-[10%] top-[15px] h-px bg-hairline" />
        <motion.span
          aria-hidden
          className="absolute left-[10%] top-[15px] h-px origin-left bg-bone-dim"
          style={{ width: "80%" }}
          initial={false}
          animate={{ scaleX: progress }}
          transition={SPRING_SETTLE}
        />

        {PHASES.map((phase, i) => {
          const Icon = ICON[phase.id];
          const live = i === index && state.fsm !== "done";
          const reached = i < index || (state.fsm === "done" && i <= index);
          const tone =
            phase.id === "verdict" && contested
              ? { text: "text-struck", ring: "border-struck/60 bg-struck/10", fill: "bg-struck" }
              : ACTOR[phase.id];
          const lit = live || (phase.id === "verdict" && state.fsm === "done");

          return (
            <li
              key={phase.id}
              aria-current={live ? "step" : undefined}
              className="relative flex flex-col items-center text-center"
            >
              <span
                className={[
                  "relative z-10 flex h-[31px] w-[31px] items-center justify-center rounded-full border transition-colors duration-300",
                  lit ? `${tone.ring} ${tone.text}` : reached ? "border-bone-dim/40 bg-ink-3 text-bone-dim" : "border-hairline bg-ink-2 text-bone-faint",
                ].join(" ")}
              >
                {live && (
                  <motion.span
                    aria-hidden
                    className={`absolute inset-0 rounded-full ${tone.fill}`}
                    initial={{ opacity: 0.35, scale: 1 }}
                    animate={{ opacity: 0, scale: 1.8 }}
                    transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
                  />
                )}
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <span
                className={[
                  "mt-1.5 font-sans text-xs font-medium",
                  lit ? tone.text : reached ? "text-bone-dim" : "text-bone-faint",
                ].join(" ")}
              >
                {phase.label}
              </span>
              <span className="mt-0.5 hidden max-w-[11rem] font-sans text-[11px] leading-snug text-bone-faint md:block">
                {phase.hint}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
