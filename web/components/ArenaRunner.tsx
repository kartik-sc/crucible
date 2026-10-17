"use client";

import { useEffect, useRef, useState } from "react";
import { MotionConfig } from "framer-motion";
import type { Domain } from "@/lib/view-model";
import type { RunRequest } from "@/lib/types";
import { useCrucibleStream } from "@/hooks/useCrucibleStream";
import { MOCK_RUN } from "@/lib/mock-stream";
import { Arena } from "./Arena";

/**
 * Owns the operator controls (domain + query) and the stream. On mount it
 * auto-plays the mock so the arena is alive immediately; against a live backend it
 * stays idle until the operator submits, so page loads don't spend a real run.
 */
export function ArenaRunner() {
  const [domain, setDomain] = useState<Domain>(MOCK_RUN.domain);
  const [query, setQuery] = useState(MOCK_RUN.query);
  const lastReq = useRef<RunRequest>(MOCK_RUN);
  const { state, status, isLive, start } = useCrucibleStream({
    domain: MOCK_RUN.domain,
    query: MOCK_RUN.query,
  });

  useEffect(() => {
    if (!isLive) start(MOCK_RUN);
  }, [isLive, start]);

  const run = (req: RunRequest) => {
    lastReq.current = req;
    start(req);
  };

  const busy = status === "running" || status === "connecting";

  return (
    <MotionConfig reducedMotion="user">
      <Arena
        state={state}
        domain={domain}
        onDomainChange={setDomain}
        query={query}
        onQueryChange={setQuery}
        onSubmit={() => run({ domain, query })}
        onRetry={() => start(lastReq.current)}
        status={status}
        running={busy}
        isLive={isLive}
      />
    </MotionConfig>
  );
}
