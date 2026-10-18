import { describe, it, expect } from "vitest";
import { readFileSync, readdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseSseFrame } from "../sse-parser";
import { createInitialState, reduceAll } from "../reducer";
import type { SseEvent } from "../types";

// Contract test: a raw /run SSE recording (server/scripts/record_run.py) must flow
// through the exact parser + reducer the frontend uses, with zero parse errors and a
// terminal DONE. A mismatch here is a backend contract bug, not a UI bug.
const FIXTURES = resolve(dirname(fileURLToPath(import.meta.url)), "fixtures");

function replay(file: string) {
  const raw = readFileSync(resolve(FIXTURES, file), "utf8");
  const frames = raw.split(/\r?\n\r?\n/).map((f) => f.trim()).filter(Boolean);
  const events: SseEvent[] = [];
  const unparsed: string[] = [];
  for (const frame of frames) {
    if (frame.startsWith(":")) continue; // SSE comment / heartbeat
    const event = parseSseFrame(frame);
    if (event === null) unparsed.push(frame.slice(0, 80));
    else events.push(event);
  }
  const state = reduceAll(createInitialState({ domain: "code", query: "replay" }), events);
  return { frameCount: frames.length, events, unparsed, state };
}

const recordings = readdirSync(FIXTURES).filter((f) => f.endsWith(".sse"));

describe("replay recorded /run SSE through the web parser + reducer", () => {
  it("has recordings to replay", () => {
    expect(recordings.length).toBeGreaterThan(0);
  });

  for (const file of recordings) {
    it(`${file}: zero parse errors and reaches DONE`, () => {
      const r = replay(file);
      expect(r.unparsed, `unparsed frames: ${r.unparsed.join(" | ")}`).toEqual([]);
      expect(r.events.length).toBeGreaterThan(0);
      expect(r.state.done, "reducer never reached a terminal DONE").not.toBeNull();
    });
  }
});
