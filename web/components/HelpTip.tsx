"use client";

import { useId, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Info } from "lucide-react";
import { cn } from "@/lib/cn";

/** A small "?" for jargon. It opens on hover or keyboard focus and closes on blur or Escape. */
export function HelpTip({
  label,
  children,
  className,
  align = "right",
}: {
  label: string;
  children: ReactNode;
  className?: string;
  align?: "left" | "right";
}) {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span
      className={cn("inline-flex", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span className="relative inline-flex">
        <button
          type="button"
          aria-label={label}
          aria-describedby={open ? id : undefined}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={(e) => e.key === "Escape" && setOpen(false)}
          onClick={() => setOpen((o) => !o)}
          className="relative z-10 rounded-full p-1 text-bone-faint transition-colors hover:text-bone focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
        >
          <Info className="h-3.5 w-3.5" aria-hidden />
        </button>
        <AnimatePresence>
          {open && (
            <motion.span
              id={id}
              role="tooltip"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 2 }}
              transition={{ duration: 0.15 }}
              className={cn(
                "absolute top-8 z-30 w-60 rounded-lg border border-hairline bg-ink-3 px-3 py-2.5 text-left font-sans text-xs leading-relaxed text-bone shadow-panel",
                align === "right" ? "right-0" : "left-0",
              )}
            >
              {children}
            </motion.span>
          )}
        </AnimatePresence>
      </span>
    </span>
  );
}
