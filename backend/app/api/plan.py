"""Business plan (mind-map data), versions, node history and AI-negotiated edits."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, orchestrator, owned_venture
from app.api.views import plan_view
from app.errors import NotFound
from app.models import Conversation, EvidenceRecord, NegotiationSession, Venture
from app.schemas.api import ChatMessageIn, NegotiationDecision, NegotiationOpen
from app.services import plan_versioning
from app.workflows.orchestrator import Orchestrator

router = APIRouter(prefix="/api/ventures/{venture_id}", tags=["plan"])


@router.get("/plan")
def get_plan(version: int | None = None, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    view = plan_view(db, venture, version)
    if view is None:
        raise NotFound("No approved plan yet.")
    return view


@router.get("/plan/nodes/{node_id}")
def node_detail(node_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    plan = plan_versioning.get_plan(db, venture.id)
    if plan is None:
        raise NotFound("No approved plan yet.")
    node = next((n for n in plan_versioning.get_version(db, plan).data["nodes"] if n["id"] == node_id), None)
    if node is None:
        raise NotFound("Node not found.")
    evidence = db.scalars(select(EvidenceRecord).where(EvidenceRecord.venture_id == venture.id, EvidenceRecord.node_id == node_id))
    return {
        "node": node,
        "evidence": [{"id": e.id, "claim": e.claim, "classification": e.classification, "source_url": e.source_url,
                      "source_title": e.source_title, "retrieved_at": e.retrieved_at.isoformat() if e.retrieved_at else None,
                      "limitations": e.limitations, "verification_status": e.verification_status} for e in evidence],
        "history": [{"from_version": r.from_version, "to_version": r.to_version, "summary": r.summary, "approved_by": r.approved_by,
                     "at": r.created_at.isoformat()} for r in plan_versioning.node_history(db, plan, node_id)],
    }


def _session_view(db: Session, s: NegotiationSession) -> dict[str, Any]:
    conv = db.get(Conversation, s.conversation_id)
    messages = [{"id": m.id, "role": m.role, "agent": m.agent, "content": m.content, "structured": m.structured,
                 "created_at": m.created_at.isoformat()} for m in (conv.messages if conv else [])]
    return {"id": s.id, "node_id": s.node_id, "base_version": s.base_version, "status": s.status,
            "proposed_change": s.proposed_change, "messages": messages}


def _session(db: Session, venture: Venture, session_id: str) -> NegotiationSession:
    s = db.get(NegotiationSession, session_id)
    if s is None or s.venture_id != venture.id:
        raise NotFound("Negotiation not found.")
    return s


@router.post("/negotiations", status_code=201)
def open_negotiation(body: NegotiationOpen, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    session, _ = orch.open_negotiation(body.node_id, body.message)
    orch.db.commit()
    return _session_view(orch.db, session)


@router.get("/negotiations/{session_id}")
def get_negotiation(session_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    return _session_view(db, _session(db, venture, session_id))


@router.post("/negotiations/{session_id}/messages")
def negotiation_message(session_id: str, body: ChatMessageIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    session = _session(orch.db, orch.venture, session_id)
    orch.negotiation_message(session, body.message)
    orch.db.commit()
    return _session_view(orch.db, session)


@router.post("/negotiations/{session_id}/decision")
def negotiation_decision(session_id: str, body: NegotiationDecision, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    session = _session(orch.db, orch.venture, session_id)
    result = orch.decide_negotiation(session, body.decision, body.expected_version, body.reason)
    orch.db.commit()
    return {**result, "negotiation": _session_view(orch.db, session), "plan": plan_view(orch.db, orch.venture)}
