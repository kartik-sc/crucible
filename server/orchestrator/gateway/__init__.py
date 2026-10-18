"""CRUCIBLE Model Gateway — provider abstraction with key-pool rotation.

Public surface:
    from gateway import build_gateway, ModelGateway, CallResult, Usage
    gw = build_gateway()                       # from env (.env)
    res = await gw.builder(messages, max_tokens=512)
    results = await gw.breaker_fanout([...])   # concurrent, least-inflight spread
"""
from .config import build_gateway
from .adapter import DevGateway, GatewayResult, ModelGatewayAdapter
from .errors import (
    AllKeysCoolingError,
    ConfigError,
    GatewayError,
    GatewayExhausted,
    KeyAuthError,
    NonRetryableError,
    RetryableError,
)
from .gateway import Endpoint, ModelGateway, UsageMeter
from .keypool import KeyPool, KeyState
from .providers import AIStudioProvider, CallResult, GroqProvider, Usage

# M2 callers import this name as the frozen gateway protocol.
Gateway = ModelGatewayAdapter

__all__ = [
    "build_gateway", "Gateway", "ModelGateway", "Endpoint", "UsageMeter",
    "DevGateway", "GatewayResult", "ModelGatewayAdapter",
    "KeyPool", "KeyState",
    "GroqProvider", "AIStudioProvider", "CallResult", "Usage",
    "GatewayError", "ConfigError", "RetryableError", "KeyAuthError",
    "NonRetryableError", "AllKeysCoolingError", "GatewayExhausted",
]
