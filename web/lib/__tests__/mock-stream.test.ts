import { describe, it, expect } from "vitest";
import {
  MOCK_EVENTS,
  MOCK_RUN,
  mockCrucibleStream,
  mockEventsFor,
  mockRunFor,
} from "../mock-stream";
import { createInitialState, reduceAll } from "../reducer";
import { DOMAINS } from "../view-model";

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

describe("per-domain runs", () => {
  it.each([...DOMAINS])("%s folds into a converged, all-green final state", (domain) => {
    const final = reduceAll(createInitialState(mockRunFor(domain)), mockEventsFor(domain));

    expect(final.done).toEqual({ reason: "converged", robustness: 0.95 });
    expect(final.builder?.version).toBe(2);
    expect(final.attacks).toHaveLength(5);
    expect(final.attacks.every((a) => a.verdict === "survived")).toBe(true);
  });

  it("the factual run shows amber (unsupported) and red (struck) side by side", () => {
    const events = mockEventsFor("factual");
    const throughRound1 = events.slice(0, events.findIndex((e) => e.type === "ROUND_END") + 1);
    const mid = reduceAll(createInitialState(mockRunFor("factual")), throughRound1);
    const colors = mid.attacks.map((a) => a.verdict);
    expect(colors).toContain("struck"); // CONTRADICTED orbit claim
    expect(colors).toContain("unsupported"); // UNSUPPORTED first-stars claim
    expect(colors).toContain("survived"); // SUPPORTED launch date + mirror
  });
});

describe("mockCrucibleStream", () => {
  it("plays the script for the requested domain", async () => {
    const controller = new AbortController();
    const seen = [];
    for await (const event of mockCrucibleStream(mockRunFor("math"), controller.signal, {
      speed: 1000,
    })) {
      seen.push(event);
    }
    expect(seen).toEqual([...mockEventsFor("math")]);
    const firstBuilder = seen.find((e) => e.type === "BUILDER");
    expect(firstBuilder && "contentPreview" in firstBuilder && firstBuilder.contentPreview).toContain(
      "S(n)",
    );
  });

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
