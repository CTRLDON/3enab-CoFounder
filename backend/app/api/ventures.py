"""Ventures: creation, summary, discovery, stop/reopen, adaptive theme, JSON export."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_founder, db_session, orchestrator, owned_venture
from app.api.views import artifact_summary, gate_view, phases_view, plan_view, venture_view
from app.models import EvidenceRecord, Founder, GateDecision, GeneratedArtifact, Venture
from app.schemas.api import ReasonIn, VentureCreate
from app.workflows.orchestrator import Orchestrator
from app.workflows.state_machine import VentureState

router = APIRouter(prefix="/api/ventures", tags=["ventures"])


@router.post("", status_code=201)
def create_venture(body: VentureCreate, founder: Founder = Depends(current_founder), db: Session = Depends(db_session)) -> dict[str, Any]:
    scenario = (body.demo_scenario or "main") if body.mode == "demo" else None
    venture = Venture(founder_id=founder.id, state=VentureState.ONBOARDING.value, mode=body.mode, demo_scenario=scenario,
                      title="Untitled venture")
    db.add(venture)
    db.commit()
    return venture_view(db, venture)


@router.get("")
def list_ventures(founder: Founder = Depends(current_founder), db: Session = Depends(db_session)) -> list[dict[str, Any]]:
    rows = db.scalars(select(Venture).where(Venture.founder_id == founder.id).order_by(Venture.created_at.desc()))
    return [{"id": v.id, "title": v.title, "state": v.state, "mode": v.mode, "created_at": v.created_at.isoformat()} for v in rows]


@router.get("/{venture_id}")
def get_venture(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    return venture_view(db, venture)


@router.post("/{venture_id}/discovery")
def run_discovery(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    insights = orch.run_founder_discovery()
    orch.db.commit()
    return {"insights": insights, "venture": venture_view(orch.db, orch.venture)}


@router.post("/{venture_id}/stop")
def stop(body: ReasonIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    orch.stop(body.reason)
    orch.db.commit()
    return venture_view(orch.db, orch.venture)


@router.post("/{venture_id}/reopen")
def reopen(body: ReasonIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    orch.reopen(body.reason)
    orch.db.commit()
    return venture_view(orch.db, orch.venture)


@router.get("/{venture_id}/theme")
def theme(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    return orch.theme()


@router.get("/{venture_id}/export")
def export(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    evidence = db.scalars(select(EvidenceRecord).where(EvidenceRecord.venture_id == venture.id))
    gates = db.scalars(select(GateDecision).where(GateDecision.venture_id == venture.id).order_by(GateDecision.created_at))
    artifacts = db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.venture_id == venture.id))
    return {
        "format": "mate-venture-export/1",
        "venture": venture_view(db, venture),
        "plan": plan_view(db, venture),
        "phases": phases_view(db, venture),
        "evidence": [{"claim": r.claim, "classification": r.classification, "source_url": r.source_url, "source_title": r.source_title,
                      "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None, "confidence": r.confidence,
                      "limitations": r.limitations, "node_id": r.node_id, "verification_status": r.verification_status} for r in evidence],
        "gate_history": [gate_view(g) for g in gates],
        "artifacts": [artifact_summary(a) for a in artifacts],
    }
