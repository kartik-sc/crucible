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

from config import settings
from contracts import Domain, RunRequest
from orchestrator import events as ev
from orchestrator.loop import CrucibleRun
from orchestrator.wiring import build_agents, get_gateway

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="CRUCIBLE orchestrator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

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
    if gw is None or not hasattr(gw, "usage"):
        return {}
    return gw.usage.summary()
