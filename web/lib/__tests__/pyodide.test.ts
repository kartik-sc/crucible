import { describe, it, expect } from "vitest";
import { buildHarnessScript, codeFnName } from "../pyodide";

describe("codeFnName", () => {
  it("extracts the defined function name", () => {
    expect(codeFnName("def fib(n):\n    return n")).toBe("fib");
    expect(codeFnName('def  sum_to (n) :\n    pass')).toBe("sum_to");
  });

  it("returns null when there is no def", () => {
    expect(codeFnName("x = 1 + 2")).toBeNull();
  });
});

describe("buildHarnessScript", () => {
  it("embeds the code, the calls, and a JSON result", () => {
    const script = buildHarnessScript("def fib(n):\n    return n", [
      { label: "n=0 edge case", expr: "fib(0)" },
      { label: "negative", expr: "fib(-1)" },
    ]);

    expect(script).toContain("def fib(n):");
    expect(script).toContain('[["n=0 edge case","fib(0)"],["negative","fib(-1)"]]');
    expect(script).toContain("eval(_expr)"); // sandboxed Python eval
    expect(script).toContain("except Exception as _e:");
    expect(script.trim().endsWith("_json.dumps(_out)")).toBe(true);
  });
});
