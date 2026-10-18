"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { ArenaState } from "@/lib/view-model";
import { tallyOf, toPercent } from "@/lib/tally";
import { SPRING_SETTLE } from "@/lib/motion";
import DecryptedText from "./fx/DecryptedText";
import { NumberTicker } from "./fx/NumberTicker";
import { PlayIcon } from "./icons/play";
import { CopyIcon } from "./icons/copy";

function plural(n: number, word: string) {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** The one-line story of a finished run, written for someone seeing it cold. */
function summaryOf(state: ArenaState) {
  const t = tallyOf(state);
  const rounds = plural(state.round, "round");
  if (t.landed === 0) return `No attack landed in ${rounds}`;
  const landed = `${plural(t.landed, "attack")} landed`;
  if (t.struck === 0) return `${landed}, all patched, ${rounds}`;
  return `${landed}, ${t.struck} still standing after ${rounds}`;
}

const ACTION =
  "inline-flex items-center gap-1.5 rounded-lg border border-hairline bg-ink-2/70 px-3 py-2 font-sans text-xs text-bone transition-colors hover:border-bone-dim/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60";

function CopyAnswer({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard
      ?.writeText(content)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1600);
      })
      .catch(() => setCopied(false));
  };
  return (
    <button type="button" onClick={copy} className={ACTION}>
      <CopyIcon size={14} aria-hidden />
      <span aria-live="polite">{copied ? "Copied" : "Copy answer"}</span>
    </button>
  );
}

/**
 * The final ruling, shown once the run is done: a full-width strip with the
 * decrypted verdict word, the plain-language tally, and the robustness ticking up.
 */
export function VerdictBanner({
  state,
  onReplay,
}: {
  state: ArenaState;
  onReplay: () => void;
}) {
  const done = state.done;
  const hardened = done !== null && tallyOf(state).struck === 0;
  const tone = hardened ? "text-survived" : "text-struck";

  return (
    <AnimatePresence>
      {done && (
        <motion.section
          key="verdict"
          aria-label="Final verdict"
          initial={{ opacity: 0, y: -8, clipPath: "inset(0 50% 0 50%)" }}
          animate={{ opacity: 1, y: 0, clipPath: "inset(0 0% 0 0%)" }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ ...SPRING_SETTLE, duration: 0.7 }}
          className={[
            "relative mb-4 overflow-hidden rounded-xl border px-5 py-4 sm:px-7",
            hardened
              ? "border-survived/30 bg-[linear-gradient(90deg,rgba(70,217,160,0.13),rgba(70,217,160,0.02)_55%,transparent)]"
              : "border-struck/30 bg-[linear-gradient(90deg,rgba(229,72,77,0.14),rgba(229,72,77,0.02)_55%,transparent)]",
          ].join(" ")}
        >
          <div className="terminal-glow pointer-events-none absolute inset-0" aria-hidden />
          <div className="relative flex flex-wrap items-center justify-between gap-x-8 gap-y-3">
            <div className="flex flex-wrap items-baseline gap-x-5 gap-y-1">
              <span
                className={`shadow-stamp -rotate-2 rounded-[4px] px-3 py-1.5 font-serif text-2xl font-semibold uppercase tracking-[0.14em] sm:text-3xl ${tone} text-glow`}
              >
                <DecryptedText
                  text={hardened ? "Hardened" : "Contested"}
                  animateOn="view"
                  sequential
                  speed={55}
                  characters="ABCDEFGHIJKLMNOPQRSTUVWXYZ#%&*+=/<>"
                  encryptedClassName="opacity-50"
                />
              </span>
              <p className="font-serif text-lg italic text-bone sm:text-xl">{summaryOf(state)}</p>
            </div>

            <div className="flex flex-wrap items-center gap-5">
              <div className="flex items-baseline gap-2">
                <span className={`flex items-start font-serif leading-none ${tone} text-glow`}>
                  <NumberTicker value={toPercent(done.robustness)} className="text-5xl" />
                  <span className="mt-1 text-xl">%</span>
                </span>
                <span className="font-sans text-sm text-bone-dim">robustness</span>
              </div>
              <div className="flex items-center gap-2">
                {state.builder && <CopyAnswer content={state.builder.contentPreview} />}
                <button type="button" onClick={onReplay} className={ACTION}>
                  <PlayIcon size={14} aria-hidden />
                  Replay
                </button>
              </div>
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
}
