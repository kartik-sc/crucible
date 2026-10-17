"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ArenaState, Domain } from "@/lib/view-model";
import type { RunRequest } from "@/lib/types";
import { createInitialState, reduce } from "@/lib/reducer";
import { crucibleStream, IS_LIVE, type CrucibleStream } from "@/lib/stream-source";

export type RunStatus = "idle" | "connecting" | "running" | "done" | "error";

export interface UseCrucibleStream {
  state: ArenaState;
  status: RunStatus;
  isLive: boolean;
  start: (req: RunRequest) => void;
  stop: () => void;
}

/**
 * Subscribe a CrucibleStream, fold its events through the reducer, and expose the
 * resulting ArenaState. The stream factory is injectable so tests can drive it
 * synchronously; production uses the env-switched default.
 */
export function useCrucibleStream(
  initial: { domain: Domain; query: string },
  createStream: CrucibleStream = crucibleStream,
): UseCrucibleStream {
  const [state, setState] = useState<ArenaState>(() => createInitialState(initial));
  const [running, setRunning] = useState(false);
  const [received, setReceived] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
  }, []);

  const start = useCallback(
    (req: RunRequest) => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState(createInitialState(req));
      setReceived(false);
      setRunning(true);

      void (async () => {
        try {
          for await (const event of createStream(req, controller.signal)) {
            if (controller.signal.aborted) return;
            setReceived(true);
            setState((prev) => reduce(prev, event));
          }
        } catch (err) {
          if (!controller.signal.aborted) {
            const message = err instanceof Error ? err.message : "stream failed";
            setState((prev) => reduce(prev, { type: "ERROR", where: "stream", message }));
          }
        } finally {
          if (abortRef.current === controller) {
            abortRef.current = null;
            setRunning(false);
          }
        }
      })();
    },
    [createStream],
  );

  useEffect(() => () => abortRef.current?.abort(), []);

  const status: RunStatus = state.error
    ? "error"
    : state.done
      ? "done"
      : running
        ? received
          ? "running"
          : "connecting"
        : "idle";

  return { state, status, isLive: IS_LIVE, start, stop };
}
