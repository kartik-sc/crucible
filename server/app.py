"""CRUCIBLE orchestrator — FastAPI entrypoint (TRD §3).

  POST /run        start a crucible run; text/event-stream of CONTRACTS §4 events
  POST /mock/run   same stream from scripted fake agents (M3 builds against this)
  GET  /mock/run   ?domain=code|factual|math — EventSource-friendly mock
  GET  /health     { ok, agents, pools }
  GET  /usage      gateway usage summary
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import Settings, settings
from contracts import Domain, RunRequest
from orchestrator import events as ev
from orchestrator.loop import CrucibleRun
from orchestrator.wiring import build_agents, get_gateway

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # per-request lines carry provider URLs

from orchestrator.seams import active_seams  # noqa: E402

logging.getLogger("crucible").info("real seams at boot: %s", active_seams(settings))


def add_cors(app: FastAPI, s: Settings) -> None:
    """Exact origins from CORS_ORIGINS, plus this project's Vercel preview deploys."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(s.cors_origins),
        allow_origin_regex=s.cors_origin_regex,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )


app = FastAPI(title="CRUCIBLE orchestrator")
add_cors(app, settings)

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


async def _stream(query: str, domain: Domain, mock: bool) -> AsyncIterator[str]:
    try:
        agents = build_agents(domain, settings, mock=mock)
    except Exception as exc:
        yield ev.error("wiring", f"{type(exc).__name__}: {exc}", fatal=True).sse()
        return
    async for e in CrucibleRun(query, domain, agents, settings).events():
        yield e.sse()


def _sse(query: str, domain: Domain, mock: bool) -> StreamingResponse:
    return StreamingResponse(_stream(query, domain, mock), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/run")
async def run(req: RunRequest) -> StreamingResponse:
    return _sse(req.query, req.domain, mock=False)


@app.post("/mock/run")
async def mock_run_post(req: RunRequest) -> StreamingResponse:
    return _sse(req.query, req.domain, mock=True)


@app.get("/mock/run")
async def mock_run_get(domain: Domain = "code", query: str = "") -> StreamingResponse:
    return _sse(query, domain, mock=True)


@app.get("/health")
async def health() -> dict:
    gw = get_gateway(settings)
    pools = gw.health() if gw is not None and hasattr(gw, "health") else []
    return {"ok": True, "agents": settings.agents, "pools": pools}


@app.get("/usage")
async def usage() -> dict:
    gw = get_gateway(settings)
    meter = getattr(gw, "usage", None)  # DevGateway without a pooled delegate has usage=None
    return meter.summary() if meter is not None else {}
