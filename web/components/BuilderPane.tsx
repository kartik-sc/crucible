"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { BuilderView, Domain } from "@/lib/view-model";
import { SPRING_PRESS, SPRING_SETTLE } from "@/lib/motion";

const DOMAIN_NOUN: Record<Domain, string> = {
  code: "the implementation",
  factual: "the answer",
  math: "the derivation",
};

export function BuilderPane({
  builder,
  domain,
  hardened = false,
}: {
  builder: BuilderView | null;
  domain: Domain;
  hardened?: boolean;
}) {
  const lines = (builder?.contentPreview ?? "").split("\n");

  return (
    <section
      className="flex min-h-[300px] flex-col bg-ink-2/60 lg:min-h-0"
      aria-label="Builder"
    >
      <header className="flex items-baseline justify-between border-b border-hairline px-5 py-4">
        <div>
          <h2 className="font-sans text-[11px] uppercase tracking-label text-bone-dim">
            Builder
          </h2>
          <p className="mt-1 font-serif text-lg text-bone">
            {hardened ? "The hardened answer" : "The defense"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AnimatePresence>
            {hardened && (
              <motion.span
                key="seal"
                initial={{ opacity: 0, scale: 0.85, filter: "blur(3px)" }}
                animate={{ opacity: 1, scale: 1, rotate: -1.5, filter: "blur(0px)" }}
                transition={SPRING_PRESS}
                className="shadow-stamp flex items-center gap-1 rounded-[3px] px-2 py-1 font-serif text-[11px] uppercase tracking-label leading-none text-survived"
                aria-label="Hardened: what survived scrutiny"
              >
                <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
                Hardened
              </motion.span>
            )}
          </AnimatePresence>
          {builder && (
            <span className="rounded-full border border-hairline px-2.5 py-1 font-mono text-xs text-accent">
              v{builder.version}
            </span>
          )}
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-5 py-4">
        <AnimatePresence mode="wait">
          {builder ? (
            <motion.pre
              key={builder.version}
              initial={{ opacity: 0, y: 8, filter: "blur(4px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -10, filter: "blur(4px)" }}
              transition={SPRING_SETTLE}
              className="font-mono text-[13px] leading-relaxed text-bone"
            >
              {lines.map((line, i) => (
                <div key={i} className="flex gap-4">
                  <span
                    aria-hidden
                    className="w-6 shrink-0 select-none text-right text-bone-faint"
                  >
                    {i + 1}
                  </span>
                  <code className="whitespace-pre-wrap">{line || " "}</code>
                </div>
              ))}
            </motion.pre>
          ) : (
            <motion.p
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="font-sans text-sm text-bone-faint"
            >
              Awaiting {DOMAIN_NOUN[domain]}…
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
