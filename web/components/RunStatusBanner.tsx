"use client";

import { AnimatePresence, motion } from "framer-motion";
import type { RunStatus } from "@/hooks/useCrucibleStream";
import type { ArenaState } from "@/lib/view-model";
import { EASE_OUT } from "@/lib/motion";

function ConnectingBar() {
  return (
    <div className="relative h-0.5 w-20 shrink-0 overflow-hidden rounded-full bg-hairline">
      <motion.div
        className="absolute inset-y-0 w-1/2 rounded-full bg-accent"
        animate={{ x: ["-100%", "220%"] }}
        transition={{ duration: 1.1, repeat: Infinity, ease: "linear" }}
      />
    </div>
  );
}

/**
 * The live-run status strip. Nothing for idle/running/done — it surfaces only the
 * two states the mock never shows: the backend waking (connecting) and a broken
 * stream (error, with Retry). Placed directly under the query, next to the action.
 */
export function RunStatusBanner({
  status,
  error,
  onRetry,
}: {
  status: RunStatus;
  error: ArenaState["error"];
  onRetry: () => void;
}) {
  return (
    <AnimatePresence mode="wait">
      {status === "connecting" && (
        <motion.div
          key="connecting"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25, ease: EASE_OUT }}
          className="flex items-center gap-3 rounded-lg border border-hairline bg-ink-2/60 px-4 py-3"
        >
          <ConnectingBar />
          <p className="font-sans text-xs text-bone-dim">
            <span className="text-bone">Summoning the swarm…</span> the backend may be
            waking — a cold start can take up to a minute.
          </p>
        </motion.div>
      )}

      {status === "error" && error && (
        <motion.div
          key="error"
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.25, ease: EASE_OUT }}
          className="flex items-center justify-between gap-4 rounded-lg border border-struck/40 bg-struck/5 px-4 py-3"
          role="alert"
        >
          <div className="min-w-0">
            <p className="font-sans text-[11px] uppercase tracking-label text-struck">
              Stream interrupted
            </p>
            <p className="mt-0.5 truncate font-mono text-xs text-bone-dim">
              {error.where}: {error.message}
            </p>
          </div>
          <button
            type="button"
            onClick={onRetry}
            className="shrink-0 rounded-lg border border-bone-dim/40 px-4 py-2 font-sans text-xs uppercase tracking-label text-bone transition-colors hover:border-bone-dim"
          >
            Retry
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
