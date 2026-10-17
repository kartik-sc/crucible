"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { VerdictColor } from "@/lib/view-model";
import { VERDICT_META } from "@/lib/ui";
import { SPRING_PRESS } from "@/lib/motion";

/**
 * The ruling. On each verdict change the old stamp lifts off and a new one presses
 * in (scale 0.85 → 1, blur → sharp) — so a patch flipping struck → survived reads
 * as the court re-ruling, not a silent recolor. `initial={false}` leaves the first
 * stamp to the row's own entrance.
 */
export function VerdictStamp({ verdict }: { verdict: VerdictColor }) {
  const meta = VERDICT_META[verdict];
  const rotate = meta.settled ? -1.5 : 0;

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.span
        key={verdict}
        initial={{ opacity: 0, scale: 0.85, rotate, filter: "blur(3px)" }}
        animate={{ opacity: meta.settled ? 1 : 0.7, scale: 1, rotate, filter: "blur(0px)" }}
        exit={{ opacity: 0, scale: 0.92, filter: "blur(3px)" }}
        transition={SPRING_PRESS}
        className={[
          "inline-flex items-center gap-1.5 rounded-[3px] px-2 py-1",
          "font-serif text-[11px] uppercase tracking-label leading-none",
          "shadow-stamp select-none",
          meta.text,
        ].join(" ")}
        aria-label={`Verdict: ${meta.label}`}
      >
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
        {meta.label}
      </motion.span>
    </AnimatePresence>
  );
}
