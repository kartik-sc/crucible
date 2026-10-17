import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Arena } from "../Arena";
import { DEMO_STATE } from "@/lib/fixtures";

describe("Arena shell", () => {
  it("mounts and renders the tribunal frame", () => {
    render(<Arena state={DEMO_STATE} />);

    expect(screen.getByRole("heading", { name: "CRUCIBLE" })).toBeInTheDocument();
    expect(screen.getByText("The defense")).toBeInTheDocument();
    expect(screen.getByText("The adversaries")).toBeInTheDocument();
  });

  it("renders the builder version and spec under trial", () => {
    render(<Arena state={DEMO_STATE} />);

    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Return the nth Fibonacci number, n >= 0."),
    ).toBeInTheDocument();
  });

  it("renders every attack with its verdict following the TR-25 grammar", () => {
    render(<Arena state={DEMO_STATE} />);

    expect(screen.getByText("n=0 edge case")).toBeInTheDocument();
    expect(screen.getAllByText("Survived")).toHaveLength(2);
    expect(screen.getByText("Struck")).toBeInTheDocument();
    expect(screen.getByText("Unsupported")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("exposes robustness as an accessible meter", () => {
    render(<Arena state={DEMO_STATE} />);

    const meter = screen.getByRole("meter", { name: "Robustness" });
    expect(meter).toHaveAttribute("aria-valuenow", "0.74");
  });
});
