"""Plan versions with optimistic concurrency.

* A plan can only be created from a proposal the founder approved (checked here, not in a prompt).
* A revision is committed only with a founder approval and only if the plan has not moved since
  the negotiation started (expected_version == current_version); otherwise VersionConflict.
* Every committed change produces a new immutable PlanVersion and NodeRevision rows.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ApprovalRequired, Forbidden, NotFound, VersionConflict
from app.models import BusinessPlan, BusinessProposal, FounderApproval, NodeRevision, PlanVersion
from app.schemas.agent_io import NodeFieldChange, PlanNodeModel, ProposedRevision
from app.schemas.common import EconomicClass

LIST_FIELDS = {"requirements", "risks", "assumptions", "validation_tasks", "next_actions"}


def get_plan(db: Session, venture_id: str) -> BusinessPlan | None:
    return db.scalars(select(BusinessPlan).where(BusinessPlan.venture_id == venture_id)).first()


def get_version(db: Session, plan: BusinessPlan, version: int | None = None) -> PlanVersion:
    wanted = version or plan.current_version
    row = db.scalars(select(PlanVersion).where(PlanVersion.plan_id == plan.id, PlanVersion.version == wanted)).first()
    if row is None:
        raise NotFound(f"Plan version {wanted} not found.")
    return row


def list_versions(db: Session, plan: BusinessPlan) -> list[PlanVersion]:
    return list(db.scalars(select(PlanVersion).where(PlanVersion.plan_id == plan.id).order_by(PlanVersion.version)))


def create_plan_from_proposal(
    db: Session,
    *,
    venture_id: str,
    proposal: BusinessProposal,
    approval: FounderApproval | None,
    document: dict[str, Any],
) -> tuple[BusinessPlan, PlanVersion]:
    if (
        approval is None
        or approval.decision != "approve"
        or approval.subject_type != "proposal"
        or approval.subject_id != proposal.id
        or proposal.status != "approved"
    ):
        raise ApprovalRequired("A business plan can only be created from a proposal you approved.")

    plan = get_plan(db, venture_id)
    if plan is None:
        plan = BusinessPlan(venture_id=venture_id, proposal_id=proposal.id, current_version=1)
        db.add(plan)
        db.flush()
        version_number, reason = 1, f"Created from approved proposal #{proposal.number}"
    else:  # pivot: a newly approved proposal replaces the plan content as a new version
        version_number = plan.current_version + 1
        plan.current_version = version_number
        plan.proposal_id = proposal.id
        reason = f"Pivot: rebuilt from newly approved proposal #{proposal.number}"
    version = PlanVersion(
        plan_id=plan.id, version=version_number, data=document, reason=reason, created_by="founder", approval_id=approval.id
    )
    db.add(version)
    db.flush()
    return plan, version


def validate_changes(document: dict[str, Any], changes: list[NodeFieldChange]) -> list[str]:
    """Return problems with a proposed revision (unknown nodes, invalid values)."""
    node_ids = {node["id"] for node in document["nodes"]}
    problems: list[str] = []
    for change in changes:
        if change.node_id not in node_ids:
            problems.append(f"Unknown node '{change.node_id}'.")
            continue
        if change.field in LIST_FIELDS and not isinstance(change.value, list):
            problems.append(f"{change.node_id}.{change.field} must be a list.")
        if change.field not in LIST_FIELDS and not isinstance(change.value, str):
            problems.append(f"{change.node_id}.{change.field} must be text.")
        if change.field == "economic_class" and change.value not in {c.value for c in EconomicClass}:
            problems.append(f"'{change.value}' is not an economic class.")
    return problems


def apply_changes(document: dict[str, Any], changes: list[NodeFieldChange]) -> dict[str, Any]:
    updated = copy.deepcopy(document)
    by_id = {node["id"]: node for node in updated["nodes"]}
    for change in changes:
        node = by_id[change.node_id]
        node[change.field] = change.value
        try:
            by_id[change.node_id] = PlanNodeModel(**node).model_dump(mode="json")
        except ValidationError as exc:
            raise Forbidden(f"Change to {change.node_id}.{change.field} is invalid: {exc.errors()[0]['msg']}") from exc
    updated["nodes"] = [by_id[node["id"]] for node in updated["nodes"]]
    venture_node = by_id.get("venture")
    if venture_node:
        updated["title"] = venture_node["title"]
        updated["one_liner"] = venture_node["summary"] or updated.get("one_liner", "")
    return updated


def commit_revision(
    db: Session,
    *,
    plan: BusinessPlan,
    revision: ProposedRevision,
    expected_version: int,
    approval: FounderApproval,
) -> PlanVersion:
    if approval.decision != "approve" or approval.subject_type != "plan_revision":
        raise ApprovalRequired("Plan revisions need an explicit founder approval.")
    if plan.current_version != expected_version:
        raise VersionConflict(
            f"The plan changed since this negotiation started (you saw v{expected_version}, current is v{plan.current_version}). "
            "Re-open the node to negotiate against the latest version.",
            expected_version=expected_version,
            current_version=plan.current_version,
        )
    current = get_version(db, plan)
    problems = validate_changes(current.data, revision.changes)
    if problems:
        raise Forbidden("The proposed revision is invalid: " + " ".join(problems))
    new_document = apply_changes(current.data, revision.changes)
    new_number = plan.current_version + 1
    version = PlanVersion(
        plan_id=plan.id,
        version=new_number,
        data=new_document,
        reason=revision.proposed_plan[:500],
        created_by="founder",
        approval_id=approval.id,
    )
    db.add(version)
    for node_id in sorted({change.node_id for change in revision.changes}):
        fields = sorted({c.field for c in revision.changes if c.node_id == node_id})
        db.add(
            NodeRevision(
                plan_id=plan.id,
                node_id=node_id,
                from_version=expected_version,
                to_version=new_number,
                summary=f"Changed {', '.join(fields)}. {revision.proposed_plan[:300]}",
                approved_by="founder",
            )
        )
    plan.current_version = new_number
    db.flush()
    return version


def node_history(db: Session, plan: BusinessPlan, node_id: str) -> list[NodeRevision]:
    return list(
        db.scalars(
            select(NodeRevision).where(NodeRevision.plan_id == plan.id, NodeRevision.node_id == node_id).order_by(NodeRevision.id)
        )
    )
