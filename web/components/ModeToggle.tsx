"use client";

import { motion } from "framer-motion";

export type RunMode = "demo" | "live";

const MODES: readonly RunMode[] = ["demo", "live"] as const;
const LABELS: Record<RunMode, string> = { demo: "Demo", live: "Live" };

/**
 * Runtime Demo ⇄ Live switch (TR-27). Shown only when a backend is configured, so
 * a judge can watch the canned demo and then submit their own input to the real
 * backend from the same URL.
 */
export function ModeToggle({
  value,
  onChange,
  disabled = false,
}: {
  value: RunMode;
  onChange: (mode: RunMode) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="tablist"
      aria-label="Run mode"
      className="inline-flex items-center gap-1 rounded-full border border-hairline bg-ink-2/70 p-1"
    >
      {MODES.map((mode) => {
        const isActive = mode === value;
        return (
          <button
            key={mode}
            role="tab"
            type="button"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => onChange(mode)}
            className={[
              "relative rounded-full px-3 py-1 font-sans text-[10px] uppercase tracking-label transition-colors duration-150",
              "disabled:cursor-not-allowed disabled:opacity-60",
              isActive ? "text-ink" : "text-bone-dim hover:text-bone",
            ].join(" ")}
          >
            {isActive && (
              <motion.span
                layoutId="mode-pill"
                className={[
                  "absolute inset-0 rounded-full",
                  mode === "live" ? "bg-survived" : "bg-accent",
                ].join(" ")}
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative z-10">{LABELS[mode]}</span>
          </button>
        );
      })}
    </div>
  );
}
