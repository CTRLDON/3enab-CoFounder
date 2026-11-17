"""Founder–AI debate, opportunity comparison, proposals and the approval decision."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, orchestrator, owned_venture
from app.api.views import plan_view, proposal_view, venture_view
from app.errors import ApprovalRequired, InvalidTransition, NotFound
from app.models import BusinessProposal, Venture
from app.schemas.api import ChatMessageIn, DecisionIn
from app.services import plan_versioning
from app.workflows.approval import latest_decision
from app.workflows.orchestrator import Orchestrator

router = APIRouter(prefix="/api/ventures/{venture_id}", tags=["debate"])


@router.get("/conversation")
def conversation(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    return {"messages": orch.history(orch.conversation("debate"))}


@router.post("/debate")
def debate(body: ChatMessageIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    result = orch.debate(body.message)
    orch.db.commit()
    return {**result, "venture": venture_view(orch.db, orch.venture)}


@router.post("/opportunities")
def opportunities(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    result = orch.compare_opportunities()
    orch.db.commit()
    return result


@router.post("/proposals", status_code=201)
def request_proposal(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    proposal = orch.request_proposal()
    orch.db.commit()
    return {"proposal": proposal_view(proposal), "venture": venture_view(orch.db, orch.venture)}


@router.post("/proposals/{proposal_id}/decision")
def decide(proposal_id: str, body: DecisionIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    result = orch.decide_proposal(proposal_id, body.decision, body.reason)
    orch.db.commit()
    return {**result, "venture": venture_view(orch.db, orch.venture), "plan": plan_view(orch.db, orch.venture)}


@router.post("/plan", status_code=201)
def create_plan_directly(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    """Exists so that bypass attempts hit an explicit, enforced check (plans are normally created by approval)."""
    if plan_versioning.get_plan(db, venture.id) is not None:
        raise InvalidTransition("A plan already exists for this venture.")
    proposal = db.query(BusinessProposal).filter_by(venture_id=venture.id).order_by(BusinessProposal.number.desc()).first()
    approval = latest_decision(db, venture.id, "proposal", proposal.id) if proposal else None
    if proposal is None or approval is None or approval.decision != "approve":
        raise ApprovalRequired("A business plan can only be created by approving a proposal.")
    raise InvalidTransition("Plans are created by the proposal decision endpoint.")


@router.get("/proposals/{proposal_id}")
def get_proposal(proposal_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    proposal = db.get(BusinessProposal, proposal_id)
    if proposal is None or proposal.venture_id != venture.id:
        raise NotFound("Proposal not found.")
    return proposal_view(proposal)
