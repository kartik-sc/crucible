"use client";

import { motion } from "framer-motion";
import type { ArenaState } from "@/lib/view-model";
import { tallyOf } from "@/lib/tally";
import { SPRING_SETTLE } from "@/lib/motion";
import { RobustnessDial } from "./RobustnessDial";
import { Sparkline } from "./Sparkline";
import { HelpTip } from "./HelpTip";
import { ShieldCheckIcon, type ShieldCheckIconHandle } from "./icons/shield-check";
import { FlameIcon, type FlameIconHandle } from "./icons/flame";
import { useIconCue } from "@/hooks/useIconCue";
import type { ArenaMoments } from "@/hooks/useArenaMoments";

interface TapeRow {
  label: string;
  builder: number;
  swarm: number;
}

/** One tale-of-the-tape line: Builder's bar grows left, the Swarm's grows right. */
function Tape({ row }: { row: TapeRow }) {
  const max = Math.max(1, row.builder, row.swarm);
  const lead = row.builder === row.swarm ? null : row.builder > row.swarm ? "builder" : "swarm";
  return (
    <div className="grid grid-cols-[2rem_minmax(0,1fr)_7.5rem_minmax(0,1fr)_2rem] items-center gap-2">
      <span
        className={`text-right font-mono text-sm tabular-nums ${lead === "builder" ? "text-builder" : "text-bone-dim"}`}
      >
        {row.builder}
      </span>
      <div className="flex h-1.5 justify-end overflow-hidden rounded-full bg-hairline">
        <motion.div
          className="h-full rounded-full bg-builder"
          initial={false}
          animate={{ width: `${(row.builder / max) * 100}%`, opacity: lead === "swarm" ? 0.45 : 1 }}
          transition={SPRING_SETTLE}
        />
      </div>
      <span className="text-center font-sans text-xs text-bone-dim">{row.label}</span>
      <div className="flex h-1.5 overflow-hidden rounded-full bg-hairline">
        <motion.div
          className="h-full rounded-full bg-swarm"
          initial={false}
          animate={{ width: `${(row.swarm / max) * 100}%`, opacity: lead === "builder" ? 0.45 : 1 }}
          transition={SPRING_SETTLE}
        />
      </div>
      <span
        className={`font-mono text-sm tabular-nums ${lead === "swarm" ? "text-swarm" : "text-bone-dim"}`}
      >
        {row.swarm}
      </span>
    </div>
  );
}

function Corner({
  side,
  name,
  role,
  record,
  detail,
  cue,
}: {
  side: "builder" | "swarm";
  name: string;
  role: string;
  record: string;
  detail: string;
  /** increments on this corner's signature moment (patch / strike). */
  cue: number;
}) {
  const builder = side === "builder";
  const shield = useIconCue<ShieldCheckIconHandle>(builder ? cue : 0);
  const flame = useIconCue<FlameIconHandle>(builder ? 0 : cue);
  return (
    <div className={`flex flex-col ${builder ? "items-start text-left" : "items-end text-right"}`}>
      <span
        className={`flex items-center gap-1.5 font-sans text-xs font-medium ${builder ? "text-builder" : "flex-row-reverse text-swarm"}`}
      >
        {builder ? (
          <ShieldCheckIcon ref={shield} size={18} aria-hidden />
        ) : (
          <FlameIcon ref={flame} size={18} aria-hidden />
        )}
        {builder ? "Defending" : "Attacking"}
      </span>
      <span className="mt-1 font-serif text-3xl font-semibold leading-none tracking-tight text-bone sm:text-4xl">
        {name}
      </span>
      <span className="mt-1.5 max-w-[16rem] font-serif text-sm italic text-bone-dim">{role}</span>
      <span className="mt-2 font-mono text-sm tabular-nums text-bone">{record}</span>
      <span className="mt-0.5 font-sans text-xs text-bone-dim">{detail}</span>
    </div>
  );
}

/**
 * The fight card: Builder in one corner, the Swarm in the other, robustness as
 * the "vs" between them, and a tale of the tape underneath.
 */
export function FightCard({ state, moments }: { state: ArenaState; moments: ArenaMoments }) {
  const t = tallyOf(state);
  const version = state.builder?.version ?? 0;
  const breakers = new Set(state.attacks.map((a) => a.breaker)).size;

  const rows: TapeRow[] = [
    { label: "Rounds won", builder: t.roundsWonBuilder, swarm: t.roundsWonSwarm },
    { label: "Held · landed", builder: t.held, swarm: t.landed },
    { label: "Patched · open", builder: t.patched, swarm: t.struck + t.open },
  ];

  return (
    <section
      aria-label="Fight card"
      className="relative overflow-hidden rounded-xl border border-hairline bg-ink-2/70 shadow-panel"
    >
      {/* corner washes: green behind the Builder, red behind the Swarm */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(60%_120%_at_0%_50%,rgba(70,217,160,0.08),transparent_60%),radial-gradient(60%_120%_at_100%_50%,rgba(229,72,77,0.09),transparent_60%)]"
      />
      <div className="terminal-glow pointer-events-none absolute inset-0" aria-hidden />

      <div className="relative grid grid-cols-2 items-center gap-4 px-5 pt-5 sm:grid-cols-[1fr_auto_1fr] sm:px-8">
        <Corner
          side="builder"
          name="Builder"
          role="Writes the answer, then patches whatever breaks"
          cue={moments.patch}
          record={version ? `v${version} on the stand` : "warming up"}
          detail={t.patched ? `${t.patched} break${t.patched === 1 ? "" : "s"} patched` : "no patches yet"}
        />
        <div className="col-span-2 row-start-2 flex flex-col items-center sm:col-span-1 sm:row-start-auto">
          <div className="relative">
            <RobustnessDial value={state.robustness} />
            <HelpTip className="absolute -right-1 top-1" label="What is robustness?">
              The share of the Swarm&rsquo;s attacks the answer survives, as ruled by the
              verifier. It climbs as the Builder patches what landed.
            </HelpTip>
          </div>
          <Sparkline values={state.robustnessHistory} />
          <span aria-hidden className="font-serif text-base italic text-bone-faint">
            vs
          </span>
        </div>
        <Corner
          side="swarm"
          name="Swarm"
          role="Tries to break it with evidence anyone can check"
          cue={moments.strike}
          record={`${t.landed} landed`}
          detail={`${breakers || "no"} breaker${breakers === 1 ? "" : "s"} engaged`}
        />
      </div>

      <div className="relative mx-auto flex max-w-xl flex-col gap-2 px-5 pb-5 pt-4">
        {rows.map((row) => (
          <Tape key={row.label} row={row} />
        ))}
      </div>
    </section>
  );
}
