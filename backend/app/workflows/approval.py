"""Founder approval: the only path by which gated work becomes 'approved'.

Approvals are created exclusively by API routes authenticated with the founder's token
(actor="founder"). Agents receive no handle to this module's write functions, and hard
policy checks run *before* an approval is recorded, so approval can never override them.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApprovalRequired, Forbidden
from app.models import FounderApproval, Venture
from app.services.audit_log import AuditLogger

APPROVAL_SUBJECTS = {
    "proposal",
    "plan_revision",
    "commercial_setup",
    "launch_package",
    "external_action",
    "support_reply",
}


def record_decision(
    db: Session,
    venture: Venture,
    *,
    subject_type: str,
    subject_id: str,
    decision: str,
    actor: str,
    reason: str,
    audit: AuditLogger,
) -> FounderApproval:
    if actor != "founder":
        raise Forbidden("Only the founder can approve or reject. Agents cannot approve their own work.")
    if subject_type not in APPROVAL_SUBJECTS:
        raise Forbidden(f"Unknown approval subject '{subject_type}'.")
    if decision not in {"approve", "reject"}:
        raise Forbidden("Decision must be 'approve' or 'reject'.")
    approval = FounderApproval(
        venture_id=venture.id,
        subject_type=subject_type,
        subject_id=subject_id,
        decision=decision,
        actor=actor,
        reason=reason,
    )
    db.add(approval)
    db.flush()
    audit.record(
        db,
        venture_id=venture.id,
        agent="founder",
        action=f"{decision}:{subject_type}",
        execution_mode="founder_action",
        approved_by="founder" if decision == "approve" else None,
        detail={"subject_id": subject_id, "reason": reason, "approval_id": approval.id},
    )
    return approval


def latest_decision(db: Session, venture_id: str, subject_type: str, subject_id: str | None = None) -> FounderApproval | None:
    query = select(FounderApproval).where(
        FounderApproval.venture_id == venture_id, FounderApproval.subject_type == subject_type
    )
    if subject_id is not None:
        query = query.where(FounderApproval.subject_id == subject_id)
    return db.scalars(query.order_by(FounderApproval.created_at.desc(), FounderApproval.id.desc())).first()


def require_approval(db: Session, venture_id: str, subject_type: str, subject_id: str | None = None) -> FounderApproval:
    approval = latest_decision(db, venture_id, subject_type, subject_id)
    if approval is None or approval.decision != "approve":
        raise ApprovalRequired(
            f"This action needs your explicit approval of the {subject_type.replace('_', ' ')} first.",
            subject_type=subject_type,
            subject_id=subject_id,
        )
    return approval
