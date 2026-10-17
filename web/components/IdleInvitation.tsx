"use client";

import { motion } from "framer-motion";

/**
 * The live first impression (replaces the panes only when live + pre-submit). A
 * designed empty state that points the judge at the one action. The bob is a
 * first-run guide cue, gated to static by the global reduced-motion config.
 */
export function IdleInvitation() {
  return (
    <div className="flex min-h-[320px] flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-center">
      <motion.span
        aria-hidden
        className="font-serif text-2xl text-bone-faint"
        animate={{ y: [0, -5, 0] }}
        transition={{ repeat: Infinity, duration: 1.8, ease: "easeInOut" }}
      >
        ↑
      </motion.span>
      <h2 className="font-serif text-xl text-bone">Put an answer on trial</h2>
      <p className="max-w-md font-sans text-sm leading-relaxed text-bone-dim">
        Type a spec or claim above and submit. The builder drafts an answer, a swarm
        of adversaries attacks it with checkable evidence, and only what survives the
        verifiers is hardened.
      </p>
    </div>
  );
}
