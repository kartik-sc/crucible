import type { ArenaState } from "@/lib/view-model";
import { BuilderPane } from "./BuilderPane";
import { SwarmPane } from "./SwarmPane";
import { RobustnessDial } from "./RobustnessDial";
import { RoundTimeline } from "./RoundTimeline";
import { DomainToggle } from "./DomainToggle";
import { QueryInput } from "./QueryInput";

export function Arena({ state }: { state: ArenaState }) {
  return (
    <div className="relative z-10 mx-auto flex min-h-screen max-w-[1400px] flex-col px-4 sm:px-6">
      <header className="flex flex-wrap items-center justify-between gap-6 py-6">
        <div>
          <h1 className="font-serif text-2xl tracking-tight text-bone">CRUCIBLE</h1>
          <p className="mt-0.5 font-sans text-[11px] uppercase tracking-label text-bone-dim">
            The answer is on trial
          </p>
        </div>
        <DomainToggle initial={state.domain} />
        <RobustnessDial value={state.robustness} />
      </header>

      <div className="pb-5">
        <QueryInput initial={state.query} />
      </div>

      <main className="grid min-h-0 flex-1 grid-cols-1 overflow-hidden rounded-xl border border-hairline shadow-panel lg:grid-cols-2 lg:divide-x lg:divide-hairline">
        <BuilderPane builder={state.builder} domain={state.domain} />
        <SwarmPane attacks={state.attacks} />
      </main>

      <footer className="mt-1 border-t border-hairline">
        <RoundTimeline state={state} />
      </footer>
    </div>
  );
}
