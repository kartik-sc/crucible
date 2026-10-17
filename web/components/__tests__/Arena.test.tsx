import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Arena, type ArenaProps } from "../Arena";
import { DEMO_STATE } from "@/lib/fixtures";

function renderArena(overrides: Partial<ArenaProps> = {}) {
  const props: ArenaProps = {
    state: DEMO_STATE,
    domain: "code",
    onDomainChange: vi.fn(),
    query: DEMO_STATE.query,
    onQueryChange: vi.fn(),
    onSubmit: vi.fn(),
    onRetry: vi.fn(),
    status: "running",
    running: false,
    isLive: false,
    ...overrides,
  };
  return render(<Arena {...props} />);
}

describe("Arena shell", () => {
  it("mounts and renders the tribunal frame", () => {
    renderArena();
    expect(screen.getByRole("heading", { name: "CRUCIBLE" })).toBeInTheDocument();
    expect(screen.getByText("The defense")).toBeInTheDocument();
    expect(screen.getByText("The adversaries")).toBeInTheDocument();
  });

  it("renders the builder version and spec under trial", () => {
    renderArena();
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Return the nth Fibonacci number, n >= 0."),
    ).toBeInTheDocument();
  });

  it("renders every attack with its verdict following the TR-25 grammar", () => {
    renderArena();
    expect(screen.getByText("n=0 edge case")).toBeInTheDocument();
    expect(screen.getAllByText("Survived")).toHaveLength(2);
    expect(screen.getByText("Struck")).toBeInTheDocument();
    expect(screen.getByText("Unsupported")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("exposes robustness as an accessible meter", () => {
    renderArena();
    const meter = screen.getByRole("meter", { name: "Robustness" });
    expect(meter).toHaveAttribute("aria-valuenow", "0.74");
  });

  it("shows the data-source badge", () => {
    renderArena({ isLive: false });
    expect(screen.getByText("Demo")).toBeInTheDocument();
  });

  it("seals the builder pane as the hardened answer when the run is done", () => {
    const doneState = {
      ...DEMO_STATE,
      done: { reason: "converged" as const, robustness: 0.95 },
    };
    renderArena({ state: doneState, status: "done" });
    expect(screen.getByText("The hardened answer")).toBeInTheDocument();
    expect(screen.getByText("Hardened")).toBeInTheDocument();
  });
});

describe("Arena — live-mode states", () => {
  it("shows the connecting banner while the backend wakes", () => {
    renderArena({ status: "connecting" });
    expect(screen.getByText(/Summoning the swarm/)).toBeInTheDocument();
  });

  it("shows an error banner with a working Retry action", () => {
    const onRetry = vi.fn();
    const errorState = {
      ...DEMO_STATE,
      error: { where: "gateway", message: "rate-limited" },
    };
    renderArena({ state: errorState, status: "error", onRetry });
    expect(screen.getByText("Stream interrupted")).toBeInTheDocument();
    expect(screen.getByText("gateway: rate-limited")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("replaces the panes with an invitation when live and idle", () => {
    renderArena({ isLive: true, status: "idle" });
    expect(screen.getByText("Put an answer on trial")).toBeInTheDocument();
    expect(screen.queryByText("The defense")).not.toBeInTheDocument();
  });

  it("keeps the panes (no invitation) in mock mode", () => {
    renderArena({ isLive: false, status: "idle" });
    expect(screen.queryByText("Put an answer on trial")).not.toBeInTheDocument();
    expect(screen.getByText("The defense")).toBeInTheDocument();
  });
});
