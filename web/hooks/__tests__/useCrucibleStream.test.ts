import { describe, it, expect } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useCrucibleStream } from "../useCrucibleStream";
import { MOCK_EVENTS, MOCK_RUN } from "@/lib/mock-stream";
import type { CrucibleStream } from "@/lib/stream-source";
import type { SseEvent } from "@/lib/types";

const immediate: CrucibleStream = async function* () {
  for (const event of MOCK_EVENTS) yield event;
};

const failing: CrucibleStream = async function* (): AsyncGenerator<SseEvent> {
  throw new Error("boom");
};

describe("useCrucibleStream", () => {
  it("starts idle with the seeded query", () => {
    const { result } = renderHook(() => useCrucibleStream(MOCK_RUN, immediate));
    expect(result.current.status).toBe("idle");
    expect(result.current.state.query).toBe(MOCK_RUN.query);
  });

  it("folds a run to a converged done state", async () => {
    const { result } = renderHook(() => useCrucibleStream(MOCK_RUN, immediate));

    act(() => result.current.start(MOCK_RUN));

    await waitFor(() => expect(result.current.status).toBe("done"));
    expect(result.current.state.robustness).toBe(0.95);
    expect(result.current.state.attacks).toHaveLength(5);
  });

  it("surfaces a thrown stream as an ERROR", async () => {
    const { result } = renderHook(() => useCrucibleStream(MOCK_RUN, failing));

    act(() => result.current.start(MOCK_RUN));

    await waitFor(() => expect(result.current.status).toBe("error"));
    expect(result.current.state.error?.message).toBe("boom");
  });
});
