/**
 * The audience-facing Pyodide mirror (TR-26). It runs the Builder's current code
 * client-side so the room can watch it execute — the server PyExec verifier stays
 * authoritative; this is a mirror, never the source of truth.
 *
 * Pyodide is a ~10 MB WASM runtime, so it is loaded lazily from a pinned CDN only
 * when the operator actually runs the mirror, and the load promise is cached. A
 * failed load resets the cache so a flaky network can be retried.
 */

const PYODIDE_VERSION = "314.0.7";
const CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

export interface HarnessCall {
  label: string;
  expr: string;
}

export interface HarnessResult {
  label: string;
  expr: string;
  output?: string;
  error?: string;
}

interface PyodideApi {
  runPython(code: string): unknown;
}

type LoadPyodide = (opts: { indexURL: string }) => Promise<PyodideApi>;

declare global {
  interface Window {
    loadPyodide?: LoadPyodide;
  }
}

/**
 * The Python program that defines the user's code then evaluates each call,
 * capturing a value or an exception per call and returning them as JSON. Pure and
 * string-only, so it can be unit-tested without the WASM runtime.
 *
 * SECURITY: the `eval(_expr)` is Python-side and runs inside the Pyodide WASM
 * sandbox — isolated from the host, with no filesystem or network access. Running
 * the Builder's (arbitrary) code is the whole point of the mirror, and the sandbox
 * is the containment boundary; `_expr` is built from a parsed function name plus
 * the swarm's own probe inputs, never host code. This is not a JS `eval`.
 */
export function buildHarnessScript(code: string, calls: HarnessCall[]): string {
  const pairs = JSON.stringify(calls.map((c) => [c.label, c.expr]));
  return [
    code,
    "",
    "import json as _json",
    "_out = []",
    `for _label, _expr in ${pairs}:`,
    "    try:",
    "        _out.append({'label': _label, 'expr': _expr, 'output': repr(eval(_expr))})",
    "    except Exception as _e:",
    "        _out.append({'label': _label, 'expr': _expr, 'error': f'{type(_e).__name__}: {_e}'})",
    "_json.dumps(_out)",
  ].join("\n");
}

/** The function name defined by a code artifact, e.g. `fib` — or null if none. */
export function codeFnName(code: string): string | null {
  const match = code.match(/def\s+(\w+)\s*\(/);
  return match ? (match[1] ?? null) : null;
}

function injectScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector("script[data-pyodide]")) return resolve();
    const el = document.createElement("script");
    el.src = src;
    el.async = true;
    el.dataset.pyodide = "true";
    el.addEventListener("load", () => resolve(), { once: true });
    el.addEventListener("error", () => reject(new Error("failed to load the Pyodide runtime")), {
      once: true,
    });
    document.head.appendChild(el);
  });
}

let pyodidePromise: Promise<PyodideApi> | null = null;

/** Lazily load Pyodide once and cache it. Resets the cache on failure for retry. */
export function getPyodide(): Promise<PyodideApi> {
  if (pyodidePromise) return pyodidePromise;
  const loading = (async () => {
    await injectScript(`${CDN}pyodide.js`);
    if (!window.loadPyodide) throw new Error("Pyodide runtime unavailable");
    return window.loadPyodide({ indexURL: CDN });
  })();
  loading.catch(() => {
    pyodidePromise = null;
  });
  pyodidePromise = loading;
  return loading;
}

/** Run the Builder's code against each call in the browser and return the results. */
export async function runHarness(code: string, calls: HarnessCall[]): Promise<HarnessResult[]> {
  const py = await getPyodide();
  const json = py.runPython(buildHarnessScript(code, calls)) as string;
  return JSON.parse(json) as HarnessResult[];
}
