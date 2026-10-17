"use client";

import { motion } from "framer-motion";
import type { AttackView } from "@/lib/view-model";
import { WEAKNESS_LABELS } from "@/lib/view-model";
import { ENTER, SPRING_SETTLE, EASE_OUT } from "@/lib/motion";
import { VerdictStamp } from "./VerdictStamp";

export function AttackRow({ attack }: { attack: AttackView }) {
  const struck = attack.verdict === "struck";

  return (
    <motion.li
      layout
      initial={ENTER.initial}
      animate={ENTER.animate}
      transition={SPRING_SETTLE}
      className="border-b border-hairline px-5 py-4 last:border-b-0"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-label text-bone-faint">
            <span className="font-sans">{WEAKNESS_LABELS[attack.breaker]}</span>
            <span aria-hidden>·</span>
            <span className="font-mono normal-case tracking-normal text-bone-dim">
              {attack.id}
            </span>
          </div>
          <p className="mt-1 truncate font-sans text-sm text-bone">{attack.rationale}</p>
          <div className="relative mt-1.5 inline-block max-w-full">
            <p className="truncate font-mono text-xs text-bone-dim">{attack.evidenceLabel}</p>
            <motion.span
              aria-hidden
              className="absolute left-0 top-1/2 h-px w-full origin-left bg-struck"
              initial={false}
              animate={{ scaleX: struck ? 1 : 0, opacity: struck ? 1 : 0 }}
              transition={{ duration: 0.4, ease: EASE_OUT }}
            />
          </div>
        </div>
        <VerdictStamp verdict={attack.verdict} />
      </div>

      {attack.evidence && (
        <p className={`mt-2.5 font-mono text-xs ${struck ? "text-struck" : "text-bone-faint"}`}>
          <span aria-hidden className="mr-1.5 opacity-60">
            ⤷
          </span>
          {attack.evidence}
        </p>
      )}
    </motion.li>
  );
}
