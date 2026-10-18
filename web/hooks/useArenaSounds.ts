"use client";

import { useEffect, useState } from "react";
import useSound from "use-sound";
import type { ArenaMoments } from "./useArenaMoments";

const STORAGE_KEY = "crucible:muted";

function readMuted(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/**
 * The arena's three sounds (use-sound): a low thud when a strike lands, a chime
 * when the Builder patches, a riser as the dial climbs. Mute defaults to off and
 * the choice is remembered per browser. Browsers hold audio until the first user
 * gesture, so the very first auto-played demo may stay silent until a click.
 */
export function useArenaSounds(moments: ArenaMoments) {
  const [muted, setMuted] = useState(false);
  useEffect(() => setMuted(readMuted()), []);

  const soundEnabled = !muted;
  const [thud] = useSound("/sfx/thud.wav", { volume: 0.55, soundEnabled });
  const [chime] = useSound("/sfx/chime.wav", { volume: 0.3, soundEnabled });
  const [riser] = useSound("/sfx/riser.wav", { volume: 0.22, soundEnabled });

  useEffect(() => {
    if (moments.strike > 0) thud();
  }, [moments.strike, thud]);
  useEffect(() => {
    if (moments.patch > 0) chime();
  }, [moments.patch, chime]);
  useEffect(() => {
    if (moments.climb > 0) riser();
  }, [moments.climb, riser]);

  const toggle = () =>
    setMuted((m) => {
      const next = !m;
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? "1" : "0");
      } catch {
        // storage blocked — the toggle still works for this visit
      }
      return next;
    });

  return { muted, toggle };
}
