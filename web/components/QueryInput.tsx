"use client";

export function QueryInput({
  value,
  onChange,
  onSubmit,
  running,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  running: boolean;
}) {
  const canSubmit = value.trim().length > 0 && !running;

  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-center"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) onSubmit();
      }}
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
          onChange={(e) => onChange(e.target.value)}
          placeholder="State the spec to put on trial…"
          className="w-full rounded-lg border border-hairline bg-ink-2/60 py-3 pl-9 pr-4 font-sans text-sm text-bone placeholder:text-bone-faint focus:border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent/30"
        />
      </div>
      <button
        type="submit"
        disabled={!canSubmit}
        className="shrink-0 rounded-lg border border-accent/40 px-5 py-3 font-sans text-xs uppercase tracking-label text-accent transition-opacity hover:bg-accent/5 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {running ? "On trial…" : "Put on trial"}
      </button>
    </form>
  );
}
