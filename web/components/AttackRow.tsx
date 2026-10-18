"use client";

import { useEffect, useId, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";
import type { AttackView, VerdictColor } from "@/lib/view-model";
import { WEAKNESS_LABELS } from "@/lib/view-model";
import { BREAKER_ICON } from "@/lib/ui";
import { ENTER, SPRING_SETTLE, EASE_OUT } from "@/lib/motion";
import { VerdictStamp } from "./VerdictStamp";
import ClickSpark, { type ClickSparkHandle } from "./fx/ClickSpark";
import { GavelIcon, type GavelIconHandle } from "./icons/gavel";

/** Leaderboard row tint + left rail, by verdict — the TR-25 grammar at row scale. */
const ROW_TONE: Record<VerdictColor, string> = {
  struck:
    "bg-[linear-gradient(90deg,rgba(229,72,77,0.16),rgba(229,72,77,0.03)_60%,transparent)] before:bg-struck",
  survived: "before:bg-survived/70",
  unsupported:
    "bg-[linear-gradient(90deg,rgba(224,169,74,0.09),transparent_60%)] before:bg-unsupported",
  pending: "before:bg-hairline",
};

const PROBE_NOUN: Record<AttackView["kind"], string> = {
  test: "Test case",
  computation: "Computation",
  claimCheck: "Claim checked",
};

/** "input → expected" for tests and computations; claims carry no expected value. */
function expectedOf(attack: AttackView): string | null {
  if (attack.kind === "claimCheck") return null;
  const [, expected] = attack.evidenceLabel.split("→");
  return expected?.trim() || null;
}

function Receipt({ attack }: { attack: AttackView }) {
  const expected = expectedOf(attack);
  const rows: { term: string; value: string; tone?: string }[] = [
    { term: PROBE_NOUN[attack.kind], value: attack.evidenceLabel },
  ];
  if (expected) rows.push({ term: "Expected", value: expected });
  if (attack.actual !== undefined) {
    rows.push({ term: "Got", value: attack.actual, tone: attack.verdict === "struck" ? "text-struck" : undefined });
  }
  rows.push({ term: "Ruling", value: attack.evidence ?? "Awaiting the verifier…" });

  return (
    <dl className="mt-3 grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 rounded-md border border-dashed border-hairline bg-ink/60 px-3 py-2.5 font-mono text-xs">
      {rows.map(({ term, value, tone }) => (
        <div key={term} className="contents">
          <dt className="text-bone-faint">{term}</dt>
          <dd className={`break-words ${tone ?? "text-bone"}`}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function AttackRow({ attack, rank }: { attack: AttackView; rank: number }) {
  const struck = attack.verdict === "struck";
  const [open, setOpen] = useState(false);
  const receiptId = useId();
  const spark = useRef<ClickSparkHandle>(null);
  const gavel = useRef<GavelIconHandle>(null);
  const prev = useRef(attack.verdict);
  const BreakerIcon = BREAKER_ICON[attack.breaker];

  // The verifier's gavel falls on every ruling; a landed strike also throws sparks.
  useEffect(() => {
    if (attack.verdict !== prev.current && attack.verdict !== "pending") gavel.current?.startAnimation();
    if (attack.verdict === "struck" && prev.current !== "struck") spark.current?.spark();
    prev.current = attack.verdict;
  }, [attack.verdict]);

  return (
    <motion.li
      layout
      initial={ENTER.initial}
      animate={ENTER.animate}
      transition={SPRING_SETTLE}
      className={[
        "relative grid grid-cols-[2rem_minmax(0,1fr)_auto] items-start gap-x-3 border-b border-hairline py-3.5 pl-4 pr-5 transition-colors duration-500 last:border-b-0",
        "before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:transition-colors before:duration-500",
        ROW_TONE[attack.verdict],
      ].join(" ")}
    >
      <span
        className={[
          "pt-0.5 font-mono text-sm tabular-nums",
          struck ? "text-struck" : "text-bone-faint",
        ].join(" ")}
      >
        {String(rank).padStart(2, "0")}
      </span>

      <div className="min-w-0">
        <div className="flex items-center gap-2 text-[11px]">
          <span className="inline-flex items-center gap-1 rounded-[3px] bg-ink-3 px-1.5 py-0.5 font-sans font-medium text-bone-dim">
            <BreakerIcon className="h-3 w-3" aria-hidden />
            {WEAKNESS_LABELS[attack.breaker]}
          </span>
          <span className="font-mono text-bone-faint">{attack.id}</span>
        </div>

        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={receiptId}
          className="group mt-1.5 flex max-w-full items-center gap-1.5 rounded text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
        >
          <span className="truncate font-sans text-[15px] font-medium text-bone">
            {attack.rationale}
          </span>
          <ChevronDown
            aria-hidden
            className={[
              "h-3.5 w-3.5 shrink-0 text-bone-faint transition-transform duration-200 group-hover:text-bone",
              open ? "rotate-180" : "",
            ].join(" ")}
          />
        </button>

        <div className="relative mt-1 inline-block max-w-full">
          <p className="truncate font-mono text-xs text-bone-dim">{attack.evidenceLabel}</p>
          <motion.span
            aria-hidden
            className="absolute left-0 top-1/2 h-px w-full origin-left bg-struck"
            initial={false}
            animate={{ scaleX: struck ? 1 : 0, opacity: struck ? 1 : 0 }}
            transition={{ duration: 0.4, ease: EASE_OUT }}
          />
        </div>
        {attack.evidence && !open && (
          <p className={`mt-1.5 font-mono text-xs ${struck ? "text-struck" : "text-bone-faint"}`}>
            <span className="mr-1.5 font-sans text-bone-faint">Verifier:</span>
            {attack.evidence}
          </p>
        )}

        <AnimatePresence initial={false}>
          {open && (
            <motion.div
              id={receiptId}
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={SPRING_SETTLE}
              className="overflow-hidden"
            >
              <Receipt attack={attack} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex items-center gap-1.5 pt-0.5">
        <GavelIcon
          ref={gavel}
          size={15}
          aria-hidden
          className={attack.verdict === "pending" ? "text-bone-faint/50" : "text-bone-faint"}
        />
        <ClickSpark
          ref={spark}
          sparkColor={["#e5484d", "#ff8a7a", "#e9e3d4"]}
          sparkCount={12}
          sparkRadius={34}
          sparkSize={9}
          duration={480}
          className="!h-auto !w-auto"
        >
          <VerdictStamp verdict={attack.verdict} />
        </ClickSpark>
      </div>
    </motion.li>
  );
}
