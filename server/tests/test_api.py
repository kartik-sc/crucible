"""TR-23: a request against /run yields a well-formed event sequence ending in DONE."""

import json

from fastapi.testclient import TestClient

import app as app_module
from config import Settings

app_module.settings = Settings(fake_delay_sec=0.0)
client = TestClient(app_module.app)


def parse_sse(body: str):
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


def test_run_streams_until_done():
    r = client.post("/run", json={"query": "Return the nth Fibonacci number, n >= 0.", "domain": "code"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    evs = parse_sse(r.text)
    assert evs[0] == ("STATE", {"state": "GENERATE", "round": 1})
    assert evs[-1][0] == "DONE" and evs[-1][1]["reason"] == "converged"


def test_mock_get_is_eventsource_friendly():
    evs = parse_sse(client.get("/mock/run", params={"domain": "factual"}).text)
    assert evs[-1][0] == "DONE"
    assert any(e == "VERDICT" and d["verdict"]["actual"] == "CONTRADICTED" for e, d in evs)


def test_bad_domain_rejected():
    assert client.post("/run", json={"query": "x", "domain": "poetry"}).status_code == 422


def test_health_and_usage():
    assert client.get("/health").json() == {"ok": True, "agents": "fake", "pools": []}
    assert client.get("/usage").json() == {}


def _cors_client() -> TestClient:
    s = Settings(cors_origins=("http://localhost:3000",), vercel_project_slug="crucible", vercel_team_slug="acme")
    api = app_module.FastAPI()
    app_module.add_cors(api, s)
    api.post("/run")(app_module.run)
    return TestClient(api)


def _preflight(c: TestClient, origin: str):
    return c.options("/run", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })


def test_cors_preflight_allows_project_preview_origin():
    origin = "https://crucible-git-feat-x-acme.vercel.app"
    r = _preflight(_cors_client(), origin)
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == origin
    assert "content-type" in r.headers["access-control-allow-headers"].lower()


def test_cors_preflight_rejects_foreign_origins():
    c = _cors_client()
    for origin in (
        "https://evil.example.com",
        "https://crucible-git-feat-x-other.vercel.app",  # same project name, other team
        "https://crucible-git-x-acme.vercel.app.evil.com",  # suffix smuggling
        "https://notcrucible-abc-acme.vercel.app",
    ):
        r = _preflight(c, origin)
        assert r.status_code == 400, origin
        assert "access-control-allow-origin" not in r.headers, origin


def test_no_team_slug_means_no_preview_regex():
    assert Settings(vercel_team_slug="").cors_origin_regex is None
