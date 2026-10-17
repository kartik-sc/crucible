import type { ArenaState } from "@/lib/view-model";
import { FSM_LABEL } from "@/lib/ui";

export function RoundTimeline({ state }: { state: ArenaState }) {
  const { round, maxRounds, rounds, fsm } = state;
  const dots = Array.from({ length: maxRounds }, (_, i) => i + 1);
  const breaksByRound = new Map(rounds.map((r) => [r.round, r.newBreaks]));
  const running = fsm !== "done" && fsm !== "idle" && fsm !== "error";

  return (
    <div className="flex items-center justify-between gap-6 px-6 py-4">
      <div className="flex items-center gap-4">
        {dots.map((n) => {
          const isCurrent = n === round && running;
          const isDone = n < round || (n === round && !running && fsm === "done");
          return (
            <div key={n} className="flex items-center gap-2">
              <span
                className={[
                  "h-2.5 w-2.5 rounded-full transition-colors duration-300 ease-settle",
                  isCurrent
                    ? "bg-accent animate-pulse"
                    : isDone
                      ? "bg-bone"
                      : "border border-hairline bg-transparent",
                ].join(" ")}
                aria-hidden
              />
              <span className="font-mono text-[11px] text-bone-faint">
                R{n}
                {breaksByRound.has(n) && (
                  <span className="ml-1 text-struck">+{breaksByRound.get(n)}</span>
                )}
              </span>
            </div>
          );
        })}
      </div>

      <span className="font-sans text-[11px] uppercase tracking-label text-bone-dim">
        {running && (
          <span
            aria-hidden
            className="mr-2 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent align-middle"
          />
        )}
        {FSM_LABEL[fsm]}
      </span>
    </div>
  );
}
