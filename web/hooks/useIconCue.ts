"use client";

import { useEffect, useRef } from "react";

interface AnimatedIconHandle {
  startAnimation: () => void;
}

/**
 * Plays a lucide-animated icon each time `cue` increments. Returns the ref to
 * hand the icon. Taking the ref also switches the icon from hover-driven to
 * moment-driven.
 */
export function useIconCue<T extends AnimatedIconHandle>(cue: number) {
  const ref = useRef<T>(null);
  useEffect(() => {
    if (cue > 0) ref.current?.startAnimation();
  }, [cue]);
  return ref;
}
