import type { ArenaState, Domain } from "@/lib/view-model";
import type { RunStatus } from "@/hooks/useCrucibleStream";
import { BuilderPane } from "./BuilderPane";
import { SwarmPane } from "./SwarmPane";
import { RobustnessDial } from "./RobustnessDial";
import { RoundTimeline } from "./RoundTimeline";
import { DomainToggle } from "./DomainToggle";
import { QueryInput } from "./QueryInput";
import { RunStatusBanner } from "./RunStatusBanner";
import { IdleInvitation } from "./IdleInvitation";

export interface ArenaProps {
  state: ArenaState;
  domain: Domain;
  onDomainChange: (domain: Domain) => void;
  query: string;
  onQueryChange: (query: string) => void;
  onSubmit: () => void;
  onRetry: () => void;
  status: RunStatus;
  running: boolean;
  isLive: boolean;
}

export function Arena({
  state,
  domain,
  onDomainChange,
  query,
  onQueryChange,
  onSubmit,
  onRetry,
  status,
  running,
  isLive,
}: ArenaProps) {
  const showInvitation = isLive && status === "idle";

  return (
    <div className="relative z-10 mx-auto flex min-h-screen max-w-[1400px] flex-col px-4 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-x-6 gap-y-4 py-6">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="font-serif text-2xl tracking-tight text-bone">CRUCIBLE</h1>
            <span
              className={[
                "rounded-full border px-2 py-0.5 font-sans text-[9px] uppercase tracking-label",
                isLive ? "border-survived/40 text-survived" : "border-hairline text-bone-faint",
              ].join(" ")}
              title={isLive ? "Streaming from the live backend" : "Running the client-side mock"}
            >
              {isLive ? "Live" : "Demo"}
            </span>
          </div>
          <p className="mt-0.5 font-sans text-[11px] uppercase tracking-label text-bone-dim">
            The answer is on trial
          </p>
        </div>
        <DomainToggle value={domain} onChange={onDomainChange} disabled={running} />
        <RobustnessDial value={state.robustness} />
      </header>

      <div className="flex flex-col gap-3 pb-5">
        <QueryInput
          value={query}
          onChange={onQueryChange}
          onSubmit={onSubmit}
          running={running}
        />
        <RunStatusBanner status={status} error={state.error} onRetry={onRetry} />
      </div>

      <main className="relative flex min-h-0 flex-1 overflow-visible rounded-xl border border-hairline shadow-panel lg:overflow-hidden">
        {showInvitation ? (
          <IdleInvitation />
        ) : (
          <div className="grid min-h-0 w-full flex-1 grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-hairline">
            <BuilderPane
              builder={state.builder}
              domain={state.domain}
              hardened={state.done !== null}
            />
            <SwarmPane attacks={state.attacks} />
          </div>
        )}
      </main>

      <footer className="mt-1 border-t border-hairline">
        <RoundTimeline state={state} />
      </footer>
    </div>
  );
}
