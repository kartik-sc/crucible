import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import type { AttackView } from "@/lib/view-model";
import { PyodideMirror } from "../PyodideMirror";
import { runHarness } from "@/lib/pyodide";

// Pyodide can't load under jsdom — mock the runner, keep codeFnName real.
vi.mock("@/lib/pyodide", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/pyodide")>();
  return { ...actual, runHarness: vi.fn() };
});

const runHarnessMock = vi.mocked(runHarness);

const CODE = "def fib(n):\n    return n";
const ATTACKS: AttackView[] = [
  { id: "a1", breaker: "boundary", kind: "test", rationale: "n=0", evidenceLabel: "0 → 0", verdict: "survived" },
  { id: "a2", breaker: "spec_gap", kind: "test", rationale: "neg", evidenceLabel: "-1 → ValueError", verdict: "struck" },
];

beforeEach(() => runHarnessMock.mockReset());

describe("PyodideMirror", () => {
  it("renders nothing when the code has no runnable probes", () => {
    const { container } = render(<PyodideMirror code="x = 1" attacks={ATTACKS} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("runs the swarm's probes and shows their in-browser output", async () => {
    runHarnessMock.mockResolvedValue([
      { label: "n=0", expr: "fib(0)", output: "0" },
      { label: "neg", expr: "fib(-1)", error: "ValueError: n >= 0" },
    ]);

    render(<PyodideMirror code={CODE} attacks={ATTACKS} />);
    fireEvent.click(screen.getByRole("button", { name: /run it yourself/i }));
    fireEvent.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText("fib(0)")).toBeInTheDocument();
    expect(screen.getByText("ValueError: n >= 0")).toBeInTheDocument();
    // The derived probe expressions match the attack inputs.
    expect(runHarnessMock).toHaveBeenCalledWith(CODE, [
      { label: "n=0", expr: "fib(0)" },
      { label: "neg", expr: "fib(-1)" },
    ]);
  });

  it("shows a graceful fallback when the sandbox fails to load", async () => {
    runHarnessMock.mockRejectedValueOnce(new Error("offline"));

    render(<PyodideMirror code={CODE} attacks={ATTACKS} />);
    fireEvent.click(screen.getByRole("button", { name: /run it yourself/i }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Run" }));
    });

    expect(screen.getByText(/couldn.t load/i)).toBeInTheDocument();
  });
});
