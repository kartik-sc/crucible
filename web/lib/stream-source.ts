/**
 * The one place that decides mock vs. live. Everything downstream consumes a
 * CrucibleStream and cannot tell which is active (web/CLAUDE.md "data source").
 *
 * The switch is NEXT_PUBLIC_API_URL: set it (to the Render backend) and the browser
 * calls the real /run directly; leave it unset and the client-side mock runs.
 *
 * NOTE (open issue #1): .env.example names this WEB_PUBLIC_API_URL, which Next.js
 * does NOT expose to the browser. The frontend needs the NEXT_PUBLIC_ prefix — a
 * frozen-file change for M1 to make. Until then, mock is the default.
 */

import type { RunRequest, SseEvent } from "./types";
import { fetchCrucibleStream } from "./sse-parser";
import { mockCrucibleStream } from "./mock-stream";

export type CrucibleStream = (
  req: RunRequest,
  signal: AbortSignal,
) => AsyncIterable<SseEvent>;

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "");

export const IS_LIVE = Boolean(API_URL);

export const crucibleStream: CrucibleStream = (req, signal) => {
  if (API_URL) return fetchCrucibleStream(`${API_URL}/run`, req, signal);
  return mockCrucibleStream(req, signal);
};
