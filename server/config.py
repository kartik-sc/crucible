"""Loop constants + service settings, read from env (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from contracts import WEAKNESS_CLASSES

try:  # local dev convenience; Render injects env directly
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # pragma: no cover
    pass


def _list(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    max_rounds: int = int(os.getenv("MAX_ROUNDS", "4"))
    max_attacks_per_breaker: int = int(os.getenv("MAX_ATTACKS_PER_BREAKER", "4"))
    sandbox_timeout_sec: float = float(os.getenv("SANDBOX_TIMEOUT_SEC", "2"))
    # Router-level ceiling per verification (sandbox timeout + retrieval/NLI slack).
    verify_timeout_sec: float = float(os.getenv("VERIFY_TIMEOUT_SEC", "8"))
    breaker_roles: tuple[str, ...] = field(
        default_factory=lambda: tuple(_list("BREAKER_ROLES", ",".join(WEAKNESS_CLASSES)))
    )
    # "fake" = scripted agents (no keys needed); "real" = M2's agents via the Gateway.
    agents: str = os.getenv("CRUCIBLE_AGENTS", "fake")
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(_list("CORS_ORIGINS", "http://localhost:3000"))
    )
    # Vercel preview deploys for this project (crucible-*.vercel.app), matched as a
    # whole-origin regex so we never open CORS to every *.vercel.app tenant.
    cors_origin_regex: str = os.getenv("CORS_ORIGIN_REGEX", r"https://crucible-[a-z0-9-]+\.vercel\.app")
    # Pacing for fake agents so the arena animates like a real run.
    fake_delay_sec: float = float(os.getenv("FAKE_DELAY_SEC", "0.4"))


settings = Settings()
