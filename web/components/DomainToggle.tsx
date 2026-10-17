"use client";

import { motion } from "framer-motion";
import type { Domain } from "@/lib/view-model";
import { DOMAINS } from "@/lib/view-model";

const LABELS: Record<Domain, string> = {
  code: "Code",
  factual: "Factual",
  math: "Math",
};

export function DomainToggle({
  value,
  onChange,
  disabled = false,
}: {
  value: Domain;
  onChange: (domain: Domain) => void;
  disabled?: boolean;
}) {
  return (
    <div
      role="tablist"
      aria-label="Domain"
      className="inline-flex items-center gap-1 rounded-full border border-hairline bg-ink-2/70 p-1"
    >
      {DOMAINS.map((domain) => {
        const isActive = domain === value;
        return (
          <button
            key={domain}
            role="tab"
            type="button"
            aria-selected={isActive}
            disabled={disabled}
            onClick={() => onChange(domain)}
            className={[
              "relative rounded-full px-3.5 py-1.5 font-sans text-xs transition-colors duration-150",
              "disabled:cursor-not-allowed disabled:opacity-60",
              isActive ? "text-ink" : "text-bone-dim hover:text-bone",
            ].join(" ")}
          >
            {isActive && (
              <motion.span
                layoutId="domain-pill"
                className="absolute inset-0 rounded-full bg-accent"
                transition={{ type: "spring", stiffness: 420, damping: 34 }}
              />
            )}
            <span className="relative z-10">{LABELS[domain]}</span>
          </button>
        );
      })}
    </div>
  );
}
