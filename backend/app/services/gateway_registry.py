"""Chooses the model gateway for a venture. Demo ventures use the scripted gateway; live ventures use the
configured provider (MODEL_PROVIDER: gemini or ollama). There is no automatic fallback from live to scripted
or between providers: a live failure is reported as a failure."""

from __future__ import annotations

from app.config import get_settings
from app.demo.scripted_gateway import ScriptedDemoGateway
from app.models import Venture
from app.services.gemini_client import GeminiGateway
from app.services.ollama_client import ModelGateway, OllamaGateway

_live_gateway: ModelGateway | None = None


def live_gateway() -> ModelGateway:
    global _live_gateway
    if _live_gateway is None:
        settings = get_settings()
        _live_gateway = GeminiGateway(settings) if settings.model_provider == "gemini" else OllamaGateway(settings)
    return _live_gateway


def set_live_gateway(gateway: ModelGateway | None) -> None:
    """Used by tests to point live ventures at a fake model server."""
    global _live_gateway
    _live_gateway = gateway


def gateway_for(venture: Venture) -> ModelGateway:
    return ScriptedDemoGateway() if venture.mode == "demo" else live_gateway()
