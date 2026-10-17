import { describe, it, expect } from "vitest";
import { createInitialState, reduce, reduceAll } from "../reducer";
import type { Attack, SseEvent } from "../types";

const base = () => createInitialState({ domain: "code", query: "fib spec" });

const codeAttack = (id: string): Attack => ({
  id,
  breaker: "boundary",
  signature: `sha256:${id}`,
  rationale: `${id} edge case`,
  test: { input: "0", expected: "0" },
});

const factualAttack = (id: string): Attack => ({
  id,
  breaker: "factual",
  signature: `sha256:${id}`,
  rationale: "claim check",
  claimCheck: { claim: "JWST launched 2021", sourceQuery: "JWST launch date" },
});

describe("reduce — single events", () => {
  it("STATE normalizes the wire name and tracks the round", () => {
    const s = reduce(base(), { type: "STATE", state: "FANOUT", round: 1 });
    expect(s.fsm).toBe("fanout");
    expect(s.round).toBe(1);
  });

  it("STATE falls back to the current fsm on an unknown name", () => {
    const start = reduce(base(), { type: "STATE", state: "VERIFY", round: 1 });
    const s = reduce(start, { type: "STATE", state: "WAT", round: 1 });
    expect(s.fsm).toBe("verify");
  });

  it("BUILDER records version and preview", () => {
    const s = reduce(base(), {
      type: "BUILDER",
      version: 2,
      contentPreview: "def fib(n): ...",
    });
    expect(s.builder).toEqual({ version: 2, contentPreview: "def fib(n): ..." });
  });

  it("ATTACK appends and derives a pending view with an evidence label", () => {
    const s = reduce(base(), { type: "ATTACK", attack: codeAttack("atk_1") });
    expect(s.attacks).toHaveLength(1);
    expect(s.attacks[0]).toMatchObject({
      id: "atk_1",
      kind: "test",
      verdict: "pending",
      evidenceLabel: "0 → 0",
    });
  });

  it("ATTACK dedups by id, preserving the existing verdict", () => {
    const withAttack = reduce(base(), { type: "ATTACK", attack: codeAttack("atk_1") });
    const settled = reduce(withAttack, {
      type: "VERDICT",
      verdict: { attackId: "atk_1", landed: true, actual: "1", evidence: "expected 0, got 1" },
    });
    const dup = reduce(settled, { type: "ATTACK", attack: codeAttack("atk_1") });
    expect(dup.attacks).toHaveLength(1);
    expect(dup.attacks[0]?.verdict).toBe("struck");
  });
});

describe("reduce — verdict color (TR-25)", () => {
  const withCode = reduce(base(), { type: "ATTACK", attack: codeAttack("c1") });
  const withFactual = reduce(base(), { type: "ATTACK", attack: factualAttack("f1") });

  it("not landed → survived", () => {
    const s = reduce(withCode, {
      type: "VERDICT",
      verdict: { attackId: "c1", landed: false, actual: "0", evidence: "matched" },
    });
    expect(s.attacks[0]?.verdict).toBe("survived");
  });

  it("landed code attack → struck", () => {
    const s = reduce(withCode, {
      type: "VERDICT",
      verdict: { attackId: "c1", landed: true, actual: "1", evidence: "expected 0, got 1" },
    });
    expect(s.attacks[0]?.verdict).toBe("struck");
  });

  it("landed factual UNSUPPORTED → unsupported (amber)", () => {
    const s = reduce(withFactual, {
      type: "VERDICT",
      verdict: { attackId: "f1", landed: true, actual: "no source", evidence: "UNSUPPORTED — no citation" },
    });
    expect(s.attacks[0]?.verdict).toBe("unsupported");
  });

  it("landed factual CONTRADICTED → struck (red)", () => {
    const s = reduce(withFactual, {
      type: "VERDICT",
      verdict: { attackId: "f1", landed: true, actual: "2022", evidence: "CONTRADICTED by source span" },
    });
    expect(s.attacks[0]?.verdict).toBe("struck");
  });

  it("a verdict for an unknown attack is ignored", () => {
    const s = reduce(withCode, {
      type: "VERDICT",
      verdict: { attackId: "ghost", landed: true, actual: "x", evidence: "y" },
    });
    expect(s.attacks[0]?.verdict).toBe("pending");
  });
});

describe("reduce — a patch flips a prior landed break to survived", () => {
  it("re-verifying the same attack after a patch updates it in place", () => {
    const events: SseEvent[] = [
      { type: "ATTACK", attack: codeAttack("atk_7f3") },
      { type: "VERDICT", verdict: { attackId: "atk_7f3", landed: true, actual: "1", evidence: "expected 0, got 1" } },
      { type: "BUILDER", version: 2, contentPreview: "patched" },
      { type: "VERDICT", verdict: { attackId: "atk_7f3", landed: false, actual: "0", evidence: "now passes" } },
    ];
    const s = reduceAll(base(), events);
    expect(s.attacks).toHaveLength(1);
    expect(s.attacks[0]?.verdict).toBe("survived");
    expect(s.builder?.version).toBe(2);
  });
});

describe("reduce — scoring and rounds", () => {
  it("SCORE sets robustness and appends to the history", () => {
    const s = reduceAll(base(), [
      { type: "SCORE", robustness: 0.4, newBreaks: 2, survived: 2, landed: 3, round: 1 },
      { type: "SCORE", robustness: 0.74, newBreaks: 1, survived: 3, landed: 4, round: 2 },
    ]);
    expect(s.robustness).toBe(0.74);
    expect(s.robustnessHistory).toEqual([0.4, 0.74]);
    expect(s.round).toBe(2);
  });

  it("ROUND_END upserts a round entry without duplicating it", () => {
    const s = reduceAll(base(), [
      { type: "ROUND_END", round: 1, newBreaks: 2 },
      { type: "ROUND_END", round: 1, newBreaks: 3 },
      { type: "ROUND_END", round: 2, newBreaks: 0 },
    ]);
    expect(s.rounds).toEqual([
      { round: 1, newBreaks: 3 },
      { round: 2, newBreaks: 0 },
    ]);
  });

  it("DONE records the reason and final robustness", () => {
    const s = reduce(base(), { type: "DONE", reason: "converged", robustness: 0.95 });
    expect(s.fsm).toBe("done");
    expect(s.done).toEqual({ reason: "converged", robustness: 0.95 });
    expect(s.robustness).toBe(0.95);
  });
});

describe("reduce — ERROR freezes the last good version", () => {
  it("surfaces the error without discarding builder, attacks or score", () => {
    const good = reduceAll(base(), [
      { type: "BUILDER", version: 1, contentPreview: "v1" },
      { type: "ATTACK", attack: codeAttack("atk_1") },
      { type: "SCORE", robustness: 0.5, newBreaks: 1, survived: 1, landed: 2, round: 1 },
    ]);
    const s = reduce(good, { type: "ERROR", where: "gateway", message: "rate-limited" });

    expect(s.fsm).toBe("error");
    expect(s.error).toEqual({ where: "gateway", message: "rate-limited" });
    expect(s.builder).toEqual(good.builder);
    expect(s.attacks).toEqual(good.attacks);
    expect(s.robustness).toBe(0.5);
  });
});

describe("reduce — purity", () => {
  it("does not mutate the previous state", () => {
    const initial = base();
    const snapshot = structuredClone(initial);
    reduce(initial, { type: "ATTACK", attack: codeAttack("atk_1") });
    expect(initial).toEqual(snapshot);
  });
});
