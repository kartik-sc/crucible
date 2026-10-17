"use client";

import { useState } from "react";

export function QueryInput({ initial = "" }: { initial?: string }) {
  const [value, setValue] = useState(initial);

  return (
    <form
      className="flex items-center gap-3"
      onSubmit={(e) => e.preventDefault()}
      aria-label="Submit an answer for trial"
    >
      <div className="relative flex-1">
        <span
          aria-hidden
          className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 font-mono text-xs text-bone-faint"
        >
          ⟩
        </span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="State the spec to put on trial…"
          className="w-full rounded-lg border border-hairline bg-ink-2/60 py-3 pl-9 pr-4 font-sans text-sm text-bone placeholder:text-bone-faint focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30"
        />
      </div>
      <button
        type="submit"
        disabled
        title="Wiring arrives in Step 3"
        className="shrink-0 rounded-lg border border-accent/40 px-5 py-3 font-sans text-xs uppercase tracking-label text-accent transition-opacity disabled:opacity-40"
      >
        Put on trial
      </button>
    </form>
  );
}
