import { describe, it, expect } from "vitest";
import { MOCK_EVENTS, MOCK_RUN, mockCrucibleStream } from "../mock-stream";
import { createInitialState, reduceAll } from "../reducer";

describe("mock script", () => {
  it("folds into a converged, all-green final state", () => {
    const final = reduceAll(createInitialState(MOCK_RUN), MOCK_EVENTS);

    expect(final.done).toEqual({ reason: "converged", robustness: 0.95 });
    expect(final.builder?.version).toBe(2);
    expect(final.robustnessHistory).toEqual([0.33, 0.95]);
    expect(final.attacks).toHaveLength(5);
    expect(final.attacks.every((a) => a.verdict === "survived")).toBe(true);
  });

  it("passes through an intermediate state with every verdict color", () => {
    // After round 1 scoring, before the patch lands.
    const throughRound1 = MOCK_EVENTS.slice(
      0,
      MOCK_EVENTS.findIndex((e) => e.type === "ROUND_END") + 1,
    );
    const mid = reduceAll(createInitialState(MOCK_RUN), throughRound1);
    const colors = mid.attacks.map((a) => a.verdict);
    expect(colors).toContain("struck");
    expect(colors).toContain("unsupported");
    expect(colors).toContain("survived");
  });
});

describe("mockCrucibleStream", () => {
  it("emits every scripted event in order at high speed", async () => {
    const controller = new AbortController();
    const seen = [];
    for await (const event of mockCrucibleStream(MOCK_RUN, controller.signal, {
      speed: 1000,
    })) {
      seen.push(event);
    }
    expect(seen).toEqual([...MOCK_EVENTS]);
  });

  it("stops early when aborted", async () => {
    const controller = new AbortController();
    const seen = [];
    for await (const event of mockCrucibleStream(MOCK_RUN, controller.signal, {
      speed: 1000,
    })) {
      seen.push(event);
      if (seen.length === 2) controller.abort();
    }
    expect(seen.length).toBeLessThan(MOCK_EVENTS.length);
  });
});
