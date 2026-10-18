"""Build a ModelGateway from environment (.env.example documents every var).

Wiring:
  builder -> Groq     (model from GROQ_BUILDER_MODEL),     temp 0.2
  breaker -> AIStudio (model from AISTUDIO_BREAKER_MODEL), temp 0.9
Each role has ONE provider and a POOL of legitimate-account keys to rotate.

Key env vars (pooled form preferred, single-key form accepted as fallback so the
same .env works with DevGateway and this gateway):
  builder: GROQ_API_KEYS (comma list)      -> fallback GROQ_API_KEY
  breaker: AISTUDIO_API_KEYS (comma list)  -> fallback GEMINI_API_KEY
"""
from __future__ import annotations

import os

from .errors import ConfigError
from .gateway import Endpoint, ModelGateway
from .keypool import KeyPool
from .providers import AIStudioProvider, GroqProvider


def _keys(pool_var: str, single_var: str) -> list[str]:
    raw = os.getenv(pool_var, "") or os.getenv(single_var, "")
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise ConfigError(
            f"{pool_var} (or {single_var}) is empty — set a comma-separated pool of "
            f"real account keys (see .env.example). Do NOT use placeholder values."
        )
    return keys


def _float(var: str, default: float) -> float:
    try:
        return float(os.getenv(var, default))
    except (TypeError, ValueError):
        return default


def build_gateway(**overrides) -> ModelGateway:
    """Construct the gateway from env vars. Pass client=... to inject a test
    transport. Raises ConfigError with an actionable message if a pool or model
    is missing.
    """
    builder_model = os.getenv("GROQ_BUILDER_MODEL")
    breaker_model = os.getenv("AISTUDIO_BREAKER_MODEL")
    if not builder_model:
        raise ConfigError("GROQ_BUILDER_MODEL is unset — set the verified Groq model id.")
    if not breaker_model:
        raise ConfigError("AISTUDIO_BREAKER_MODEL is unset — set the verified AI Studio model id.")

    endpoints = {
        "builder": Endpoint(
            provider=GroqProvider(),
            model=builder_model,
            pool=KeyPool(_keys("GROQ_API_KEYS", "GROQ_API_KEY")),
            default_temperature=_float("BUILDER_TEMPERATURE", 0.2),
        ),
        "breaker": Endpoint(
            provider=AIStudioProvider(),
            model=breaker_model,
            pool=KeyPool(_keys("AISTUDIO_API_KEYS", "GEMINI_API_KEY")),
            default_temperature=_float("BREAKER_TEMPERATURE", 0.9),
        ),
    }
    return ModelGateway(endpoints, **overrides)
