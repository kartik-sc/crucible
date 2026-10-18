"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { VerdictColor } from "@/lib/view-model";
import { VERDICT_META } from "@/lib/ui";

/** Heavy and fast: the stamp drops from above the paper and stops dead. */
const SLAM = { type: "spring", stiffness: 700, damping: 22, mass: 0.9 } as const;

/**
 * The ruling. On each verdict change the old stamp lifts off and the new one
 * slams in (scale 1.5, rotate −6, slight blur → sharp), so a patch flipping
 * struck → survived reads as the court re-ruling, not a silent recolor.
 * `initial={false}` leaves the first stamp to the row's own entrance.
 */
export function VerdictStamp({ verdict }: { verdict: VerdictColor }) {
  const meta = VERDICT_META[verdict];
  const rest = verdict === "struck" ? -3 : meta.settled ? -1.5 : 0;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={verdict}
        initial={
          meta.settled
            ? { opacity: 0, scale: 1.5, rotate: -6, filter: "blur(2px)" }
            : { opacity: 0, scale: 0.9 }
        }
        animate={{ opacity: meta.settled ? 1 : 0.65, scale: 1, rotate: rest, filter: "blur(0px)" }}
        exit={{ opacity: 0, scale: 0.92, filter: "blur(3px)", transition: { duration: 0.12 } }}
        transition={SLAM}
        className={[
          "inline-flex items-center gap-1.5 rounded-[3px] px-2.5 py-1.5",
          "font-serif text-[11px] font-semibold uppercase tracking-label leading-none",
          "shadow-stamp select-none",
          verdict === "struck" ? "bg-struck/10" : verdict === "survived" ? "bg-survived/[0.06]" : "",
          meta.text,
        ].join(" ")}
        aria-label={`Verdict: ${meta.label}`}
      >
        <span
          aria-hidden
          className={["h-1.5 w-1.5 rounded-full bg-current", meta.settled ? "" : "animate-pulse"].join(" ")}
        />
        {meta.label}
      </motion.span>
    </AnimatePresence>
  );
}
