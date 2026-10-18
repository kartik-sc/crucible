"use client";

import { useEffect, useRef } from "react";

/**
 * Single-key shortcuts for the demo operator (e.g. R = replay, M = mute). Ignored
 * while typing in a field or with a modifier held, so the query input is safe.
 */
export function useHotkeys(bindings: Record<string, () => void>) {
  const latest = useRef(bindings);
  latest.current = bindings;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.repeat) return;
      const target = e.target;
      if (target instanceof Element && target.closest("input, textarea, select, [contenteditable='true']")) {
        return;
      }
      latest.current[e.key.toLowerCase()]?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
}
