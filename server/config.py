"""Loop constants + service settings, read from env (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from contracts import WEAKNESS_CLASSES

try:  # local dev convenience; Render injects env directly
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")         # server/.env (local; keys live here)
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # repo-root .env (fallback)
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


# ---------------------------------------------------------------------------
# Per-seam real switches (read once at startup; default fake). Let a single seam
# go real at a time for incremental local bring-up on DevGateway. CRUCIBLE_AGENTS=real
# still turns everything real. See orchestrator/seams.py and .env.example.
# ---------------------------------------------------------------------------
USE_REAL_BUILDER = os.getenv("USE_REAL_BUILDER", "0") == "1"
USE_REAL_BREAKERS = tuple(_list("USE_REAL_BREAKERS", ""))  # comma list of roles, e.g. "boundary"
USE_REAL_PYEXEC = os.getenv("USE_REAL_PYEXEC", "0") == "1"
USE_REAL_NLI = os.getenv("USE_REAL_NLI", "0") == "1"
DEMO_ARTIFACT = os.getenv("DEMO_ARTIFACT", "")  # a key in demo.artifacts.ALL; else first matching the domain


# ---------------------------------------------------------------------------
# M2 swarm / verifier constants (ported from M2's orchestrator/config.py).
# Module-level so the breakers/verifiers keep `import config; config.X`.
# ---------------------------------------------------------------------------

# --- swarm ---
MAX_ATTACKS_PER_BREAKER = settings.max_attacks_per_breaker
BUILDER_TEMP = float(os.getenv("BUILDER_TEMPERATURE", "0.2"))
BREAKER_TEMPS = {"boundary": 0.8, "numeric_type": 0.9, "spec_gap": 1.0, "factual": 0.8}
BREAKER_SEEDS = {"boundary": 11, "numeric_type": 22, "spec_gap": 33, "factual": 44}

# --- token caps ---
BUILDER_MAX_TOKENS = 1600
BREAKER_MAX_TOKENS = 700
REPAIR_MAX_TOKENS = 700
LEDGER_PROMPT_CAP = 10  # survivors/landed lines shown per list in a breaker prompt

# --- sandbox (single source: Settings.sandbox_timeout_sec reads SANDBOX_TIMEOUT_SEC) ---
SANDBOX_TIMEOUT_S = settings.sandbox_timeout_sec
SANDBOX_MEMORY_MB = int(os.getenv("SANDBOX_MEMORY_MB", "512"))
SANDBOX_CONCURRENCY = int(os.getenv("SANDBOX_CONCURRENCY", "4"))

# --- NLI (DeBERTa MNLI-family entailment; never an LLM opinion) ---
NLI_BACKEND = os.getenv("NLI_BACKEND", "hf")  # hf | local
NLI_MODEL = os.getenv("NLI_MODEL", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN", "")  # .env.example names it HF_API_TOKEN
HF_NLI_URL = os.getenv("HF_NLI_URL", f"https://router.huggingface.co/hf-inference/models/{NLI_MODEL}")
NLI_THRESHOLD = float(os.getenv("NLI_THRESHOLD", "0.70"))
NLI_TOP_PASSAGES = int(os.getenv("NLI_TOP_PASSAGES", "4"))
# UNSUPPORTED claims: False = only CONTRADICTED lands (safer against weak retrieval).
UNSUPPORTED_LANDS = os.getenv("UNSUPPORTED_LANDS", "0") == "1"

# --- oracles / differential fuzzing ---
N_ORACLES = int(os.getenv("N_ORACLES", "2"))
ORACLE_TEMP = 0.5
ORACLE_SEEDS = (101, 202, 303)
FUZZ_TIMEOUT_S = 4.0
FUZZ_SAMPLES = 150
