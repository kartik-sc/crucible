"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { BuilderView, Domain } from "@/lib/view-model";
import { diffLines, plainLines, type DiffLine } from "@/lib/line-diff";
import { SPRING_SETTLE } from "@/lib/motion";

const DOMAIN_NOUN: Record<Domain, string> = {
  code: "the implementation",
  factual: "the answer",
  math: "the derivation",
};

const GUTTER: Record<DiffLine["kind"], string> = { same: " ", added: "+", removed: "−" };

const ROW: Record<DiffLine["kind"], string> = {
  same: "",
  added: "bg-survived/[0.09] shadow-[inset_2px_0_0_var(--survived)]",
  removed: "bg-struck/[0.07] shadow-[inset_2px_0_0_var(--struck)] text-bone-faint line-through decoration-struck/60",
};

export function BuilderPane({
  builder,
  domain,
  hardened = false,
  previousContent = null,
  strike = 0,
}: {
  builder: BuilderView | null;
  domain: Domain;
  hardened?: boolean;
  /** the previous version's content; null on v1, so nothing is highlighted. */
  previousContent?: string | null;
  /** increments on each landed strike — flashes the pane's red inset ring. */
  strike?: number;
}) {
  const content = builder?.contentPreview ?? "";
  const lines =
    builder && builder.version > 1 && previousContent !== null
      ? diffLines(previousContent, content)
      : plainLines(content);
  const changed = lines.filter((l) => l.kind !== "same").length;

  return (
    <section
      className="relative flex h-[75vh] max-h-[680px] min-h-[300px] flex-col bg-ink-2/60 lg:h-auto lg:max-h-none lg:min-h-0"
      aria-label="Builder"
    >
      {/* the hit: a red inset ring that flares and fades each time a strike lands */}
      <AnimatePresence>
        {strike > 0 && (
          <motion.span
            key={strike}
            aria-hidden
            className="pointer-events-none absolute inset-0 z-20 shadow-[inset_0_0_0_2px_var(--struck),inset_0_0_48px_-12px_var(--struck)]"
            initial={{ opacity: 1 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 0.9, ease: [0.4, 0, 0.2, 1] }}
          />
        )}
      </AnimatePresence>

      <header className="flex items-end justify-between gap-4 border-b border-hairline px-5 py-4">
        <div>
          <h2 className="flex items-center gap-2 font-sans text-xs font-medium text-builder">
            <span aria-hidden className="h-2 w-2 rounded-[2px] bg-builder" />
            Builder
          </h2>
          <p className="mt-1 font-serif text-xl text-bone">
            {hardened ? "The hardened answer" : "The defense"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {changed > 0 && (
            <span className="font-mono text-[11px] text-survived">
              {changed} line{changed === 1 ? "" : "s"} patched
            </span>
          )}
          {builder && (
            <motion.span
              key={builder.version}
              initial={{ scale: 1.25, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={SPRING_SETTLE}
              className="rounded-md border border-hairline bg-ink-3 px-2.5 py-1 font-mono text-xs text-accent"
            >
              v{builder.version}
            </motion.span>
          )}
        </div>
      </header>

      <div className="terminal-glow scroll-pane min-h-0 flex-1 py-3" tabIndex={0} aria-label="Builder output">
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
              {lines.map((line, i) => {
                const cells = (
                  <>
                    {domain === "code" && (
                      <span
                        aria-hidden
                        className="w-6 shrink-0 select-none text-right text-bone-faint"
                      >
                        {line.lineNo ?? ""}
                      </span>
                    )}
                    <span
                      aria-hidden
                      className={[
                        "w-3 shrink-0 select-none",
                        line.kind === "added" ? "text-survived" : "text-struck",
                      ].join(" ")}
                    >
                      {GUTTER[line.kind]}
                    </span>
                    <code className="min-w-0 flex-1 whitespace-pre-wrap [overflow-wrap:anywhere]">
                      {line.text || " "}
                    </code>
                  </>
                );
                const className = `flex gap-3 px-5 ${ROW[line.kind]}`;
                // Only patched lines animate, with a capped stagger, so a long answer
                // renders at once instead of trickling in one motion node per line.
                return line.kind === "same" ? (
                  <div key={`${line.kind}-${i}`} className={className}>
                    {cells}
                  </div>
                ) : (
                  <motion.div
                    key={`${line.kind}-${i}`}
                    className={className}
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ ...SPRING_SETTLE, delay: 0.25 + Math.min(i, 20) * 0.03 }}
                  >
                    {cells}
                  </motion.div>
                );
              })}
            </motion.pre>
          ) : (
            <motion.p
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-5 font-sans text-sm text-bone-faint"
            >
              Awaiting {DOMAIN_NOUN[domain]}…
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
