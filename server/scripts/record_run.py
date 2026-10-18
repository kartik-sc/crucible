"""Record a /run SSE stream to recordings/<domain>-<timestamp>.sse.

POSTs {query, domain} to a running orchestrator and saves the raw text/event-stream
bytes verbatim, so the recording can be replayed through the web parser/reducer
(the same contract the frontend consumes). Prints only the path and a short summary —
never any request headers or secrets.

Usage:
  python scripts/record_run.py --domain code --demo code
  python scripts/record_run.py --domain code --query "..."     [--url http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import sys

import httpx

RECORDINGS = pathlib.Path(__file__).resolve().parent.parent / "recordings"


def _query_from_demo(key: str) -> tuple[str, str]:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    import demo.artifacts as D

    demo = D.ALL[key]
    return demo.spec, demo.domain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--domain", default="code")
    ap.add_argument("--query", default=None)
    ap.add_argument("--demo", default=None, help="demo key; takes its spec + domain from demo/artifacts.py")
    args = ap.parse_args()

    domain = args.domain
    query = args.query
    if args.demo:
        query, domain = _query_from_demo(args.demo)
    if not query:
        ap.error("provide --query or --demo")

    RECORDINGS.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = RECORDINGS / f"{domain}-{stamp}.sse"

    events = 0
    done = False
    with out.open("wb") as fh:
        with httpx.stream("POST", f"{args.url.rstrip('/')}/run", json={"query": query, "domain": domain},
                          timeout=httpx.Timeout(180.0, read=180.0)) as r:
            r.raise_for_status()
            for raw in r.iter_raw():
                fh.write(raw)
                text = raw.decode("utf-8", "replace")
                events += text.count("event:")
                if "event: DONE" in text:
                    done = True

    print(f"recording: {out}")
    print(f"events (approx): {events}  reached_DONE: {done}  bytes: {out.stat().st_size}")
    return 0 if done else 2


if __name__ == "__main__":
    raise SystemExit(main())
