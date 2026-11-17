"""Venture state machine. Every transition is validated, persisted and audited."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy.orm import Session

from app.errors import InvalidTransition
from app.models import StateTransition, Venture
from app.services.audit_log import AuditLogger


class VentureState(StrEnum):
    ONBOARDING = "ONBOARDING"
    DISCOVERY = "DISCOVERY"
    DEBATE = "DEBATE"
    PROPOSAL_READY = "PROPOSAL_READY"
    AWAITING_FOUNDER_APPROVAL = "AWAITING_FOUNDER_APPROVAL"
    PLAN_APPROVED = "PLAN_APPROVED"
    WORKSPACE_ACTIVE = "WORKSPACE_ACTIVE"
    VALIDATING = "VALIDATING"
    BUILDING = "BUILDING"
    COMMERCIAL_REVIEW = "COMMERCIAL_REVIEW"
    LAUNCH_SIMULATION = "LAUNCH_SIMULATION"
    OPERATING = "OPERATING"
    PIVOT_REQUIRED = "PIVOT_REQUIRED"
    STOPPED = "STOPPED"


S = VentureState
_EXIT = {S.PIVOT_REQUIRED, S.STOPPED}

ALLOWED_TRANSITIONS: dict[VentureState, set[VentureState]] = {
    S.ONBOARDING: {S.DISCOVERY, S.STOPPED},
    S.DISCOVERY: {S.DEBATE, S.STOPPED},
    S.DEBATE: {S.PROPOSAL_READY, S.STOPPED},
    S.PROPOSAL_READY: {S.AWAITING_FOUNDER_APPROVAL, S.DEBATE, S.STOPPED},
    S.AWAITING_FOUNDER_APPROVAL: {S.PLAN_APPROVED, S.DEBATE, S.STOPPED},
    S.PLAN_APPROVED: {S.WORKSPACE_ACTIVE},
    S.WORKSPACE_ACTIVE: {S.VALIDATING, *_EXIT},
    S.VALIDATING: {S.BUILDING, *_EXIT},
    S.BUILDING: {S.COMMERCIAL_REVIEW, *_EXIT},
    S.COMMERCIAL_REVIEW: {S.LAUNCH_SIMULATION, *_EXIT},
    S.LAUNCH_SIMULATION: {S.OPERATING, *_EXIT},
    S.OPERATING: set(_EXIT),
    # Reconsideration reopens the discussion; it never relabels evidence or past gate results.
    S.PIVOT_REQUIRED: {S.DEBATE, S.STOPPED},
    S.STOPPED: {S.DEBATE},
}

# The state a venture is in while each phase's work and gate are active.
PHASE_STATE: dict[int, VentureState] = {
    1: S.WORKSPACE_ACTIVE,
    2: S.VALIDATING,
    3: S.BUILDING,
    4: S.COMMERCIAL_REVIEW,
    5: S.LAUNCH_SIMULATION,
    6: S.OPERATING,
}
PRE_WORKSPACE_STATES = {S.ONBOARDING, S.DISCOVERY, S.DEBATE, S.PROPOSAL_READY, S.AWAITING_FOUNDER_APPROVAL}


def current_phase(state: str) -> int | None:
    for phase, phase_state in PHASE_STATE.items():
        if phase_state == state:
            return phase
    if state in PRE_WORKSPACE_STATES or state == S.PLAN_APPROVED:
        return 1
    return None


def transition(
    db: Session,
    venture: Venture,
    to_state: VentureState,
    *,
    actor: str,
    reason: str,
    audit: AuditLogger,
    execution_mode: str,
) -> None:
    from_state = VentureState(venture.state)
    if to_state == from_state:
        return
    if to_state not in ALLOWED_TRANSITIONS[from_state]:
        raise InvalidTransition(
            f"A venture in {from_state} cannot move to {to_state}.",
            from_state=from_state.value,
            to_state=to_state.value,
        )
    venture.state = to_state.value
    db.add(StateTransition(venture_id=venture.id, from_state=from_state, to_state=to_state, actor=actor, reason=reason))
    audit.record(
        db,
        venture_id=venture.id,
        agent="workflow",
        action=f"transition:{from_state.value}->{to_state.value}",
        execution_mode=execution_mode,
        approved_by="founder" if actor == "founder" else None,
        detail={"reason": reason, "actor": actor},
    )
