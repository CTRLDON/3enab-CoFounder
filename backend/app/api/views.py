"""Read models returned by the API."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BusinessProposal,
    EvidenceRecord,
    GateDecision,
    GeneratedArtifact,
    NegotiationSession,
    NodeRevision,
    StateTransition,
    ValidationExperiment,
    Venture,
)
from app.services import plan_versioning
from app.workflows.orchestrator import PHASE_NAMES
from app.workflows.state_machine import PHASE_STATE, current_phase

PHASE_AGENTS = {
    1: ["founder_discovery", "skeptical_cofounder", "opportunity_evaluation", "market_research", "validation", "gatekeeper"],
    2: ["validation", "gatekeeper"],
    3: ["product_architect", "mvp_builder", "gatekeeper"],
    4: ["commercial", "gatekeeper"],
    5: ["launch", "gatekeeper"],
    6: ["operations", "gatekeeper"],
}


def proposal_view(p: BusinessProposal) -> dict[str, Any]:
    data = {k: v for k, v in p.data.items() if not k.startswith("_")}
    return {
        "id": p.id, "number": p.number, "status": p.status, "data": data,
        "policy_findings": p.data.get("_policy_findings", []), "rejection_reason": p.data.get("_rejection_reason"),
        "created_at": p.created_at.isoformat(), "decided_at": p.decided_at.isoformat() if p.decided_at else None,
    }


def gate_view(g: GateDecision) -> dict[str, Any]:
    return {"id": g.id, "phase": g.phase, "outcome": g.outcome, "checks": g.checks, "reasoning": g.reasoning,
            "evidence_basis": g.evidence_basis, "commentary": g.model_commentary, "created_at": g.created_at.isoformat()}


def artifact_summary(a: GeneratedArtifact) -> dict[str, Any]:
    return {"id": a.id, "phase": a.phase, "kind": a.kind, "title": a.title, "content_type": a.content_type,
            "labels": a.labels, "created_at": a.created_at.isoformat()}


def latest_gates(db: Session, venture_id: str) -> dict[int, GateDecision]:
    latest: dict[int, GateDecision] = {}
    for g in db.scalars(select(GateDecision).where(GateDecision.venture_id == venture_id).order_by(GateDecision.created_at)):
        latest[g.phase] = g
    return latest


def venture_view(db: Session, v: Venture) -> dict[str, Any]:
    proposals = list(db.scalars(select(BusinessProposal).where(BusinessProposal.venture_id == v.id).order_by(BusinessProposal.number)))
    plan = plan_versioning.get_plan(db, v.id)
    transitions = list(db.scalars(select(StateTransition).where(StateTransition.venture_id == v.id).order_by(StateTransition.id)))
    return {
        "id": v.id, "title": v.title, "state": v.state, "mode": v.mode, "demo_scenario": v.demo_scenario,
        "labels": ["SCRIPTED DEMO"] if v.mode == "demo" else [],
        "current_phase": current_phase(v.state),
        "founder_insights": v.founder_insights,
        "proposals": [proposal_view(p) for p in proposals],
        "plan_version": plan.current_version if plan else None,
        "gates": {str(k): gate_view(g) for k, g in latest_gates(db, v.id).items()},
        "transitions": [{"from": t.from_state, "to": t.to_state, "actor": t.actor, "reason": t.reason,
                         "at": t.created_at.isoformat()} for t in transitions],
        "created_at": v.created_at.isoformat(),
    }


def plan_view(db: Session, v: Venture, version: int | None = None) -> dict[str, Any] | None:
    plan = plan_versioning.get_plan(db, v.id)
    if plan is None:
        return None
    row = plan_versioning.get_version(db, plan, version)
    evidence: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in db.scalars(select(EvidenceRecord).where(EvidenceRecord.venture_id == v.id)):
        if r.node_id:
            evidence[r.node_id][r.classification] += 1
    revisions: dict[str, int] = defaultdict(int)
    for rev in db.scalars(select(NodeRevision).where(NodeRevision.plan_id == plan.id)):
        revisions[rev.node_id] += 1
    phase_now = current_phase(v.state) or 0
    gates = latest_gates(db, v.id)
    status: dict[str, dict[str, Any]] = {}
    for node in row.data["nodes"]:
        phase = node.get("phase", 1)
        if v.state == "STOPPED":
            progress = "stopped"
        elif phase in gates and gates[phase].outcome == "GO":
            progress = "complete"
        elif phase == phase_now:
            progress = "active"
        elif phase < phase_now:
            progress = "complete"
        else:
            progress = "upcoming"
        status[node["id"]] = {"progress": progress, "evidence": dict(evidence.get(node["id"], {})), "revisions": revisions.get(node["id"], 0)}
    return {
        "plan_id": plan.id, "version": row.version, "current_version": plan.current_version, "reason": row.reason,
        "created_by": row.created_by, "created_at": row.created_at.isoformat(), "document": row.data, "node_status": status,
        "versions": [{"version": pv.version, "reason": pv.reason, "created_by": pv.created_by, "created_at": pv.created_at.isoformat()}
                     for pv in plan_versioning.list_versions(db, plan)],
        "open_negotiations": [{"id": s.id, "node_id": s.node_id, "status": s.status} for s in db.scalars(
            select(NegotiationSession).where(NegotiationSession.venture_id == v.id, NegotiationSession.status.in_(["open", "proposed"])))],
    }


def phases_view(db: Session, v: Venture) -> list[dict[str, Any]]:
    gates = latest_gates(db, v.id)
    artifacts = list(db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.venture_id == v.id).order_by(GeneratedArtifact.created_at)))
    experiments = list(db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == v.id).order_by(ValidationExperiment.created_at)))
    phase_now = current_phase(v.state)
    out = []
    for phase in range(1, 7):
        gate = gates.get(phase)
        if v.state == PHASE_STATE[phase]:
            status = "active"
        elif gate and gate.outcome == "GO":
            status = "passed"
        elif gate and gate.outcome in ("STOP", "PIVOT") and v.state in ("STOPPED", "PIVOT_REQUIRED"):
            status = gate.outcome.lower()
        elif phase_now and phase < phase_now:
            status = "passed"
        else:
            status = "locked"
        latest_by_kind: dict[str, GeneratedArtifact] = {}
        for a in artifacts:
            if a.phase == phase:
                latest_by_kind[a.kind] = a
        out.append({
            "phase": phase, "name": PHASE_NAMES[phase], "status": status, "agents": PHASE_AGENTS[phase],
            "artifacts": [artifact_summary(a) for a in latest_by_kind.values()],
            "gate": gate_view(gate) if gate else None,
            "experiments": [{"id": e.id, "name": e.name, "metric": e.metric, "target": e.target, "window_days": e.window_days,
                             "locked_at": e.locked_at.isoformat() if e.locked_at else None,
                             "results": [{"observed": r.observed, "source": r.source, "note": r.note, "evidence_url": r.evidence_url,
                                          "at": r.created_at.isoformat()} for r in e.results]}
                            for e in experiments] if phase == 2 else [],
        })
    return out
