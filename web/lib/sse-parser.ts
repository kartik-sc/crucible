/**
 * The live transport: POST /run → read the text/event-stream → typed SseEvent.
 *
 * WIRE FRAMING (proposed to M1 — open issue #3). Each event is a standard SSE
 * frame: the event name in the `event:` field, the JSON payload in `data:`, frames
 * separated by a blank line. The payload JSON does NOT repeat the type; the parser
 * reconstructs `{ type, ...payload }`. Example:
 *
 *     event: ATTACK
 *     data: {"attack": { "id": "atk_7f3", ... }}
 *
 * EventSource is not usable here: /run is a POST with a JSON body, so we drive the
 * stream by hand with fetch + a ReadableStream reader (web/CLAUDE.md).
 */

import type { RunRequest, SseEvent, SseEventType } from "./types";
import { SSE_EVENT_TYPES } from "./types";

const KNOWN_TYPES = new Set<string>(SSE_EVENT_TYPES);

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

/** CONTRACTS §1: an attack's `id` and `signature` are required and identify it. */
function hasRequiredAttackFields(attack: unknown): boolean {
  if (typeof attack !== "object" || attack === null) return false;
  const { id, signature } = attack as { id?: unknown; signature?: unknown };
  return isNonEmptyString(id) && isNonEmptyString(signature);
}

/**
 * Parse one SSE frame (the text between blank-line separators) into a typed event,
 * or null if it is a comment/heartbeat, an unknown event, or malformed JSON.
 */
export function parseSseFrame(frame: string): SseEvent | null {
  let eventName = "";
  const dataLines: string[] = [];

  for (const rawLine of frame.split("\n")) {
    const line = rawLine.replace(/\r$/, "");
    if (line === "" || line.startsWith(":")) continue; // blank or comment
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") eventName = value;
    else if (field === "data") dataLines.push(value);
  }

  if (!KNOWN_TYPES.has(eventName) || dataLines.length === 0) return null;

  let payload: unknown;
  try {
    payload = JSON.parse(dataLines.join("\n"));
  } catch {
    return null;
  }
  if (typeof payload !== "object" || payload === null) return null;

  const event = { type: eventName as SseEventType, ...(payload as object) } as SseEvent;

  // The rest of the pipeline joins verdicts to attacks by id, so an ATTACK missing
  // its required id/signature is dropped here (logged, never thrown) rather than
  // seeding a malformed row the reducer would then try to match against.
  if (event.type === "ATTACK" && !hasRequiredAttackFields(event.attack)) {
    console.warn("[sse-parser] dropping ATTACK with missing id/signature", event.attack);
    return null;
  }

  return event;
}

/**
 * Drive the live /run stream. Yields typed events as they arrive; throws on a
 * non-OK response so the hook can surface an ERROR. Cancels cleanly on abort.
 */
export async function* fetchCrucibleStream(
  endpoint: string,
  req: RunRequest,
  signal: AbortSignal,
): AsyncGenerator<SseEvent> {
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(req),
    signal,
  });

  if (!res.ok || !res.body) {
    throw new Error(`POST ${endpoint} responded ${res.status}`);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      // Normalize on the whole buffer, not the chunk: a \r\n\r\n frame separator
      // can straddle two reads, and per-chunk replacement would miss it.
      buffer = (buffer + value).replace(/\r\n/g, "\n");

      let brk: number;
      while ((brk = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, brk);
        buffer = buffer.slice(brk + 2);
        const event = parseSseFrame(frame);
        if (event) yield event;
      }
    }
    const tail = parseSseFrame(buffer);
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}
