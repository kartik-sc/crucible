"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MotionConfig } from "framer-motion";
import type { Domain } from "@/lib/view-model";
import type { RunRequest } from "@/lib/types";
import { useCrucibleStream } from "@/hooks/useCrucibleStream";
import { MOCK_RUN, mockRunFor } from "@/lib/mock-stream";
import {
  IS_LIVE,
  liveCrucibleStream,
  mockCrucibleStream,
  type CrucibleStream,
} from "@/lib/stream-source";
import { Arena } from "./Arena";
import type { RunMode } from "./ModeToggle";

/**
 * Owns the operator controls (domain + query), the Demo/Live mode, and the stream.
 * Demo mode auto-plays the scripted run on mount and replays it on domain change;
 * Live mode (only when a backend is configured) stays idle until a judge submits.
 */
export function ArenaRunner() {
  const [domain, setDomain] = useState<Domain>(MOCK_RUN.domain);
  const [query, setQuery] = useState(MOCK_RUN.query);
  const [mode, setMode] = useState<RunMode>("demo");
  const lastReq = useRef<RunRequest>(MOCK_RUN);
  const modeRef = useRef<RunMode>("demo");

  // Stable factory that dispatches on the current mode at call time, so the hook's
  // start() keeps a stable identity across mode changes.
  const createStream = useCallback<CrucibleStream>((req, signal) => {
    return modeRef.current === "live" && IS_LIVE
      ? liveCrucibleStream(req, signal)
      : mockCrucibleStream(req, signal);
  }, []);

  const { state, status, start, reset } = useCrucibleStream(
    { domain: MOCK_RUN.domain, query: MOCK_RUN.query },
    createStream,
  );

  // Auto-play the demo on mount; live mode waits for a judge to submit.
  useEffect(() => {
    if (modeRef.current === "demo") start(MOCK_RUN);
  }, [start]);

  const live = mode === "live";

  const run = (req: RunRequest) => {
    lastReq.current = req;
    start(req);
  };

  // Demo mode: the DomainToggle replays the domain's scripted run. Live mode: it
  // only selects the domain — the judge types their own query and submits.
  const changeDomain = (next: Domain) => {
    setDomain(next);
    if (live) return;
    const req = mockRunFor(next);
    setQuery(req.query);
    run(req);
  };

  const changeMode = (next: RunMode) => {
    if (next === mode) return;
    setMode(next);
    modeRef.current = next;
    if (next === "live") {
      lastReq.current = { domain, query }; // retry before submit should re-arm, not replay the demo
      reset({ domain, query }); // clean idle — the judge submits their own input
    } else {
      const req = mockRunFor(domain);
      setQuery(req.query);
      run(req); // resume the canned demo
    }
  };

  const busy = status === "running" || status === "connecting";

  return (
    <MotionConfig reducedMotion="user">
      <Arena
        state={state}
        domain={domain}
        onDomainChange={changeDomain}
        query={query}
        onQueryChange={setQuery}
        onSubmit={() => run({ domain, query })}
        onRetry={() => start(lastReq.current)}
        status={status}
        running={busy}
        isLive={live}
        canGoLive={IS_LIVE}
        mode={mode}
        onModeChange={changeMode}
      />
    </MotionConfig>
  );
}
