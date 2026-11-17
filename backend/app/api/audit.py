"""Audit trail and decision history."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, owned_venture
from app.models import AgentRun, AuditEvent, Venture
from app.services.audit_log import decision_log_entry

router = APIRouter(prefix="/api/ventures/{venture_id}", tags=["audit"])


@router.get("/audit")
def audit(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    events = db.scalars(select(AuditEvent).where(AuditEvent.venture_id == venture.id).order_by(AuditEvent.id))
    runs = db.scalars(select(AgentRun).where(AgentRun.venture_id == venture.id).order_by(AgentRun.created_at))
    return {
        "events": [{**decision_log_entry(e), "id": e.id, "detail": e.detail} for e in events],
        "agent_runs": [{"id": r.id, "agent": r.agent, "task": r.task, "status": r.status, "model": r.model,
                        "execution_mode": r.execution_mode, "error": r.error, "prompt_tokens": r.prompt_tokens,
                        "completion_tokens": r.completion_tokens, "duration_ms": r.duration_ms, "attempts": r.attempts,
                        "created_at": r.created_at.isoformat()} for r in runs],
        "cost_note": "cost = direct paid-API fees in USD (0 on the Gemini free tier and for local models). Electricity and hardware are real but not metered per call.",
    }
