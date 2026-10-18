import { describe, it, expect, vi, afterEach } from "vitest";
import { parseSseFrame, fetchCrucibleStream } from "../sse-parser";
import type { SseEvent } from "../types";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < chunks.length) controller.enqueue(encoder.encode(chunks[i++]));
      else controller.close();
    },
  });
}

async function collect(chunks: string[]): Promise<SseEvent[]> {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(streamOf(chunks), { status: 200 })),
  );
  const out: SseEvent[] = [];
  for await (const e of fetchCrucibleStream("/run", { domain: "code", query: "q" }, new AbortController().signal)) {
    out.push(e);
  }
  return out;
}

describe("parseSseFrame", () => {
  it("merges the event name and data payload into a typed event", () => {
    const event = parseSseFrame('event: VERDICT\ndata: {"verdict":{"attackId":"a1","landed":true,"actual":"1","evidence":"x"}}');
    expect(event).toEqual({
      type: "VERDICT",
      verdict: { attackId: "a1", landed: true, actual: "1", evidence: "x" },
    });
  });

  it("tolerates missing leading space and CRLF line endings", () => {
    const event = parseSseFrame("event:DONE\r\ndata:{\"reason\":\"converged\",\"robustness\":0.9}\r");
    expect(event).toEqual({ type: "DONE", reason: "converged", robustness: 0.9 });
  });

  it("joins multiple data lines before parsing", () => {
    const event = parseSseFrame('event: ERROR\ndata: {"where":"gateway",\ndata: "message":"cooling"}');
    expect(event).toEqual({ type: "ERROR", where: "gateway", message: "cooling" });
  });

  it("ignores comments / heartbeats", () => {
    expect(parseSseFrame(": keep-alive")).toBeNull();
  });

  it("drops an unknown event name", () => {
    expect(parseSseFrame('event: GOSSIP\ndata: {"x":1}')).toBeNull();
  });

  it("drops malformed JSON instead of throwing", () => {
    expect(parseSseFrame("event: STATE\ndata: {not json}")).toBeNull();
  });

  const validAttack =
    'event: ATTACK\ndata: {"attack":{"id":"atk_1","breaker":"boundary","signature":"sha256:abc","rationale":"r","test":{"input":"0","expected":"0"}}}';

  it("keeps an ATTACK that has both id and signature", () => {
    const event = parseSseFrame(validAttack);
    expect(event).toMatchObject({ type: "ATTACK", attack: { id: "atk_1", signature: "sha256:abc" } });
  });

  it("drops an ATTACK missing its id and logs it, without throwing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const event = parseSseFrame(
      'event: ATTACK\ndata: {"attack":{"breaker":"boundary","signature":"sha256:abc","rationale":"r","test":{"input":"0","expected":"0"}}}',
    );
    expect(event).toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });

  it("drops an ATTACK missing its signature and logs it, without throwing", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const event = parseSseFrame(
      'event: ATTACK\ndata: {"attack":{"id":"atk_1","breaker":"boundary","rationale":"r","test":{"input":"0","expected":"0"}}}',
    );
    expect(event).toBeNull();
    expect(warn).toHaveBeenCalledOnce();
    warn.mockRestore();
  });
});

describe("fetchCrucibleStream", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reassembles a CRLF frame separator split across two reads", async () => {
    const frame = 'event: STATE\r\ndata: {"state":"GENERATE","round":1}\r\n';
    const whole = frame + "\r\n" + frame; // two frames joined by the blank-line separator
    // Cut mid-separator: "\r\n\r\n" → "...\r\n\r" | "\n...". Per-chunk normalization
    // would miss this boundary; buffer-level normalization must still find it.
    const cut = whole.indexOf("\r\n\r\n") + 3;
    const events = await collect([whole.slice(0, cut), whole.slice(cut)]);
    expect(events).toHaveLength(2);
    expect(events[0]).toMatchObject({ type: "STATE", state: "GENERATE", round: 1 });
    expect(events[1]).toMatchObject({ type: "STATE", state: "GENERATE", round: 1 });
  });
});
