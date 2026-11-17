"""Health, configuration status and demo scenario fixtures."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.agents.commercial import CommercialAgent
from app.agents.founder_discovery import FounderDiscoveryAgent
from app.agents.gatekeeper import GatekeeperAgent
from app.agents.launch import LaunchAgent
from app.agents.market_research import MarketResearchAgent
from app.agents.mvp_builder import MvpBuilderAgent
from app.agents.operations import OperationsAgent
from app.agents.opportunity_evaluation import OpportunityEvaluationAgent
from app.agents.product_architect import ProductArchitectAgent
from app.agents.skeptical_cofounder import SkepticalCofounderAgent
from app.agents.validation import ValidationAgent
from app.config import get_settings
from app.demo.scenarios import DEMO_FOUNDERS, FOUNDER_SCRIPT
from app.services.gateway_registry import live_gateway

router = APIRouter(prefix="/api", tags=["system"])

AGENTS = [FounderDiscoveryAgent, SkepticalCofounderAgent, OpportunityEvaluationAgent, MarketResearchAgent, ValidationAgent,
          ProductArchitectAgent, MvpBuilderAgent, CommercialAgent, LaunchAgent, OperationsAgent, GatekeeperAgent]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/system/status")
def status(check_model: bool = True) -> dict[str, Any]:
    settings = get_settings()
    model: dict[str, Any] = {"provider": settings.model_provider, "model": settings.active_model, "checked": False}
    if check_model:
        gateway = live_gateway()
        found = gateway.status() if hasattr(gateway, "status") else {"reachable": True, "model_installed": True}
        model = {**model, **found, "checked": True}
    return {
        "default_mode": settings.mate_default_mode,
        "model": model,
        "external_actions_enabled": settings.external_actions_enabled,
        "payments": settings.payments_mode,
        "research_online": settings.research_online,
        "agents": [{"name": a.name, "responsibility": a.responsibility, "tools": list(a.tools), "prompt": f"prompts/{a.prompt_file}"} for a in AGENTS],
    }


@router.get("/demo/scenarios")
def demo_scenarios() -> dict[str, Any]:
    return {
        "label": "SCRIPTED DEMO",
        "note": "Demo ventures use scripted agent responses (no model). Gates, approvals, mocks and logging run as normal.",
        "scenarios": {key: {"founder": DEMO_FOUNDERS[key], "script": FOUNDER_SCRIPT[key]} for key in DEMO_FOUNDERS},
    }
