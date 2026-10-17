import { describe, it, expect } from "vitest";
import { parseSseFrame } from "../sse-parser";

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
});
