"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { AttackView } from "@/lib/view-model";
import { codeFnName, runHarness, type HarnessResult } from "@/lib/pyodide";
import { SPRING_SETTLE } from "@/lib/motion";

interface Probe {
  label: string;
  expr: string;
  expected: string;
}

type Status = "idle" | "loading" | "ready" | "error";

/** Build the probe calls from the swarm's own code attacks, so the mirror runs the
 *  exact cases the breakers raised (evidenceLabel is "input → expected"). */
function deriveProbes(code: string, attacks: AttackView[]): Probe[] {
  const name = codeFnName(code);
  if (!name) return [];
  const seen = new Set<string>();
  const probes: Probe[] = [];
  for (const attack of attacks) {
    if (attack.kind !== "test") continue;
    const [rawInput, rawExpected] = attack.evidenceLabel.split("→");
    const input = rawInput?.trim() ?? "";
    const expr = `${name}(${input})`;
    if (!input || seen.has(expr)) continue;
    seen.add(expr);
    probes.push({ label: attack.rationale, expr, expected: rawExpected?.trim() ?? "" });
  }
  return probes;
}

function passed(result: HarnessResult, expected?: string): boolean | undefined {
  if (!expected) return undefined;
  const actual = result.output ?? result.error ?? "";
  if (!actual) return false;
  return actual.includes(expected) || expected.includes(actual);
}

export function PyodideMirror({ code, attacks }: { code: string; attacks: AttackView[] }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<(HarnessResult & { expected?: string })[]>([]);

  const probes = deriveProbes(code, attacks);
  if (probes.length === 0) return null;

  const run = () => {
    setStatus("loading");
    runHarness(
      code,
      probes.map((p) => ({ label: p.label, expr: p.expr })),
    )
      .then((out) => {
        const expectedByExpr = new Map(probes.map((p) => [p.expr, p.expected]));
        setResults(out.map((r) => ({ ...r, expected: expectedByExpr.get(r.expr) })));
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  };

  const runLabel =
    status === "loading" ? "Warming the sandbox…" : status === "ready" ? "Run again" : "Run";

  return (
    <section className="mt-3 overflow-hidden rounded-xl border border-hairline" aria-label="Pyodide mirror">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-5 py-3 text-left transition-colors hover:bg-ink-2/60"
      >
        <span className="flex items-baseline gap-2">
          <span className="font-serif text-sm text-bone">Run it yourself</span>
          <span className="font-sans text-[11px] text-bone-dim">in your browser · unofficial</span>
        </span>
        <span
          aria-hidden
          className="font-mono text-xs text-bone-faint transition-transform"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        >
          ▸
        </span>
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={SPRING_SETTLE}
            className="border-t border-hairline"
          >
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
              <p className="max-w-md font-sans text-[11px] leading-relaxed text-bone-dim">
                Runs the current code in a Python sandbox in your browser. The server verifier
                stays authoritative — this is the audience mirror.
              </p>
              <button
                type="button"
                onClick={run}
                disabled={status === "loading"}
                className="shrink-0 rounded-full border border-accent/50 px-4 py-1.5 font-sans text-[11px] uppercase tracking-label text-accent transition-colors hover:bg-accent/10 disabled:opacity-60"
              >
                {runLabel}
              </button>
            </div>

            {status === "error" && (
              <p className="px-5 pb-4 font-sans text-xs text-unsupported">
                The in-browser sandbox couldn’t load (it needs network access). The server verdicts
                above are unaffected.
              </p>
            )}

            {status === "ready" && (
              <ul className="space-y-1.5 px-5 pb-4">
                {results.map((r) => {
                  const ok = passed(r, r.expected);
                  const actual = r.output ?? r.error ?? "";
                  return (
                    <li
                      key={r.expr}
                      className="flex items-center justify-between gap-4 font-mono text-xs"
                    >
                      <span className="text-bone">{r.expr}</span>
                      <span className="flex items-center gap-2">
                        <span className={r.error ? "text-struck" : "text-bone-dim"}>{actual}</span>
                        {ok !== undefined && (
                          <span
                            aria-hidden
                            className={[
                              "h-1.5 w-1.5 rounded-full",
                              ok ? "bg-survived" : "bg-struck",
                            ].join(" ")}
                          />
                        )}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
