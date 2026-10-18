"use client";

import type { ArenaState, Domain } from "@/lib/view-model";
import type { RunStatus } from "@/hooks/useCrucibleStream";
import { BuilderPane } from "./BuilderPane";
import { SwarmPane } from "./SwarmPane";
import { RobustnessDial } from "./RobustnessDial";
import { RoundTimeline } from "./RoundTimeline";
import { DomainToggle } from "./DomainToggle";
import { ModeToggle, type RunMode } from "./ModeToggle";
import { QueryInput } from "./QueryInput";
import { RunStatusBanner } from "./RunStatusBanner";
import { IdleInvitation } from "./IdleInvitation";
import { PyodideMirror } from "./PyodideMirror";
import { FightCard } from "./FightCard";
import { PhaseRail } from "./PhaseRail";
import { RoundIntro } from "./RoundIntro";
import { VerdictBanner } from "./VerdictBanner";
import { SoundToggle } from "./SoundToggle";
import { BorderBeam } from "./fx/BorderBeam";
import { useArenaMoments } from "@/hooks/useArenaMoments";
import { useArenaSounds } from "@/hooks/useArenaSounds";
import { useHotkeys } from "@/hooks/useHotkeys";

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
  canGoLive: boolean;
  mode: RunMode;
  onModeChange: (mode: RunMode) => void;
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
  canGoLive,
  mode,
  onModeChange,
}: ArenaProps) {
  const showInvitation = isLive && status === "idle";
  const showMirror = !showInvitation && state.domain === "code" && state.builder !== null;
  const moments = useArenaMoments(state);
  const sound = useArenaSounds(moments);
  const fighting = status === "running" || status === "connecting";
  useHotkeys({ r: () => !running && onRetry(), m: sound.toggle });

  return (
    <div className="relative z-10 mx-auto flex min-h-screen max-w-[1400px] flex-col px-4 sm:px-6">
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-4 pb-5 pt-7">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-serif text-4xl font-semibold leading-none tracking-[-0.02em] text-bone sm:text-5xl">
              CRUCIBLE
            </h1>
            {canGoLive ? (
              <ModeToggle value={mode} onChange={onModeChange} />
            ) : (
              <span
                className="rounded-[3px] border border-accent/40 px-2 py-1 font-sans text-[10px] font-semibold uppercase leading-none tracking-label text-accent"
                title="Running the client-side mock"
              >
                Demo
              </span>
            )}
          </div>
          <p className="mt-2 font-serif text-lg italic text-bone-dim">
            The answer is on trial. Only what survives the swarm reaches you.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <DomainToggle value={domain} onChange={onDomainChange} disabled={running} />
          <SoundToggle muted={sound.muted} onToggle={sound.toggle} />
        </div>
      </header>

      <FightCard state={state} moments={moments} />
      {!showInvitation && (
        <div className="mt-3">
          <PhaseRail state={state} />
        </div>
      )}

      <div className="flex flex-col gap-3 py-4">
        <QueryInput
          value={query}
          onChange={onQueryChange}
          onSubmit={onSubmit}
          running={running}
        />
        <RunStatusBanner status={status} error={state.error} onRetry={onRetry} />
      </div>

      <VerdictBanner state={state} onReplay={onRetry} />

      <main className="relative flex min-h-0 flex-1 overflow-visible rounded-xl border border-hairline bg-ink/60 shadow-panel lg:overflow-hidden">
        <RoundIntro state={state} />
        {fighting && <BorderBeam size={140} duration={7} colorFrom="#e0a94a" colorTo="#e5484d" borderWidth={1.5} />}
        {showInvitation ? (
          <IdleInvitation />
        ) : (
          <div className="grid min-h-0 w-full flex-1 grid-cols-1 lg:grid-cols-2 lg:divide-x lg:divide-hairline">
            <BuilderPane
              builder={state.builder}
              domain={state.domain}
              hardened={state.done !== null}
              previousContent={moments.previousContent}
              strike={moments.strike}
            />
            <SwarmPane attacks={state.attacks} />
          </div>
        )}
      </main>

      {showMirror && state.builder && (
        <PyodideMirror code={state.builder.contentPreview} attacks={state.attacks} />
      )}

      <footer className="mt-3 border-t border-hairline">
        <RoundTimeline state={state} />
      </footer>
    </div>
  );
}
