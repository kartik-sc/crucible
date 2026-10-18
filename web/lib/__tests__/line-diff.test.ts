import { describe, it, expect } from "vitest";
import { diffLines, plainLines } from "../line-diff";

describe("diffLines", () => {
  it("marks replaced lines as removed then added, keeping shared lines", () => {
    const out = diffLines("a\nb\nc", "a\nB\nc\nd");
    expect(out.map((l) => `${l.kind}:${l.text}`)).toEqual([
      "same:a",
      "removed:b",
      "added:B",
      "same:c",
      "added:d",
    ]);
  });

  it("numbers lines by the new version", () => {
    const out = diffLines("x", "x\ny");
    expect(out.map((l) => l.lineNo)).toEqual([1, 2]);
  });

  it("leaves the first version unhighlighted", () => {
    expect(plainLines("p\nq").every((l) => l.kind === "same")).toBe(true);
  });
});
