import { describe, it, expect } from "vitest";
import { tallyOf, toPercent } from "../tally";
import { DEMO_STATE } from "../fixtures";

describe("tallyOf", () => {
  it("scores rounds: any new break goes to the Swarm", () => {
    const t = tallyOf({ ...DEMO_STATE, rounds: [{ round: 1, newBreaks: 3 }, { round: 2, newBreaks: 0 }] });
    expect(t.roundsWonSwarm).toBe(1);
    expect(t.roundsWonBuilder).toBe(1);
    expect(t.landed).toBe(3);
    expect(t.rounds[2]?.winner).toBeNull();
  });

  it("counts patched breaks as landed minus those still struck or unsupported", () => {
    const t = tallyOf(DEMO_STATE); // 3 landed across rounds, 1 still struck, 1 unsupported
    expect(t.struck).toBe(1);
    expect(t.patched).toBe(1);
  });
});

describe("toPercent", () => {
  it("clamps and rounds", () => {
    expect(toPercent(0.954)).toBe(95);
    expect(toPercent(null)).toBe(0);
    expect(toPercent(1.4)).toBe(100);
  });
});

describe("tallyOf — live round", () => {
  it("counts strikes on the board before the round settles", () => {
    const t = tallyOf({ ...DEMO_STATE, round: 1, rounds: [] });
    expect(t.landed).toBe(1);
    expect(t.patched).toBe(0);
  });
});

describe("tallyOf — re-verification round", () => {
  it("does not double-count earlier breaks that are still struck", () => {
    const t = tallyOf({ ...DEMO_STATE, round: 2, rounds: [{ round: 1, newBreaks: 3 }] });
    expect(t.landed).toBe(3);
  });
});
