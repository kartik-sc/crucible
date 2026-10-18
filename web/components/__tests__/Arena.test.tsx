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
    canGoLive: false,
    mode: "demo",
    onModeChange: vi.fn(),
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
      attacks: DEMO_STATE.attacks.map((a) =>
        a.verdict === "struck" ? { ...a, verdict: "survived" as const } : a,
      ),
      done: { reason: "converged" as const, robustness: 0.95 },
    };
    renderArena({ state: doneState, status: "done" });
    expect(screen.getByText("The hardened answer")).toBeInTheDocument();
    expect(screen.getByText("Hardened")).toBeInTheDocument();
    expect(screen.getByText("3 attacks landed, all patched, 2 rounds")).toBeInTheDocument();
  });

  it("calls the run contested when a strike is still standing at the end", () => {
    const doneState = {
      ...DEMO_STATE,
      done: { reason: "max_rounds" as const, robustness: 0.74 },
    };
    renderArena({ state: doneState, status: "done" });
    expect(screen.getByText("Contested")).toBeInTheDocument();
    expect(screen.getByText("3 attacks landed, 1 still standing after 2 rounds")).toBeInTheDocument();
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

describe("Arena — judge-live mode (TR-27)", () => {
  it("shows only the Demo badge when no backend is configured", () => {
    renderArena({ canGoLive: false });
    expect(screen.getByText("Demo")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Live" })).not.toBeInTheDocument();
  });

  it("offers a Demo/Live toggle when a backend is configured", () => {
    const onModeChange = vi.fn();
    renderArena({ canGoLive: true, mode: "demo", onModeChange });
    expect(screen.getByRole("tab", { name: "Demo" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Live" }));
    expect(onModeChange).toHaveBeenCalledWith("live");
  });
});

describe("Arena — pass 2 readability", () => {
  it("lights the current trial phase on the rail", () => {
    renderArena(); // DEMO_STATE is mid-verify
    const rail = screen.getByRole("navigation", { name: "Trial progress" });
    const current = rail.querySelector('[aria-current="step"]');
    expect(current).toHaveTextContent("Verify");
  });

  it("expands an attack into its evidence receipt", () => {
    renderArena();
    fireEvent.click(screen.getByRole("button", { name: /n=0 edge case/ }));
    expect(screen.getByText("Expected")).toBeInTheDocument();
    expect(screen.getByText("expected 0, got 1")).toBeInTheDocument();
  });

  it("offers Replay on the final verdict", () => {
    const onRetry = vi.fn();
    const doneState = { ...DEMO_STATE, done: { reason: "converged" as const, robustness: 0.95 } };
    renderArena({ state: doneState, status: "done", onRetry });
    fireEvent.click(screen.getByRole("button", { name: "Replay" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("replays on R, but not while typing in the query", () => {
    const onRetry = vi.fn();
    renderArena({ onRetry });
    fireEvent.keyDown(screen.getByDisplayValue(DEMO_STATE.query), { key: "r" });
    expect(onRetry).not.toHaveBeenCalled();
    fireEvent.keyDown(window, { key: "r" });
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
