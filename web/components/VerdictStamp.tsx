import type { VerdictColor } from "@/lib/view-model";
import { VERDICT_META } from "@/lib/ui";

export function VerdictStamp({ verdict }: { verdict: VerdictColor }) {
  const meta = VERDICT_META[verdict];

  return (
    <span
      className={[
        "inline-flex items-center gap-1.5 rounded-[3px] px-2 py-1",
        "font-serif text-[11px] uppercase tracking-label leading-none",
        "shadow-stamp select-none",
        meta.text,
        meta.settled ? "opacity-100" : "opacity-70",
      ].join(" ")}
      style={{ transform: meta.settled ? "rotate(-1.5deg)" : "none" }}
      aria-label={`Verdict: ${meta.label}`}
    >
      <span
        aria-hidden
        className={`h-1.5 w-1.5 rounded-full bg-current ${
          meta.settled ? "" : "animate-pulse"
        }`}
      />
      {meta.label}
    </span>
  );
}
