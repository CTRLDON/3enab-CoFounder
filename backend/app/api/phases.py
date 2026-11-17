"""Six-phase pipeline: run a phase's agents, evaluate its gate, record results, approvals and evidence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, orchestrator, owned_venture
from app.api.views import gate_view, phases_view, venture_view
from app.errors import Forbidden, InvalidTransition, NotFound
from app.models import EvidenceRecord, ExperimentResult, ValidationExperiment, Venture
from app.schemas.api import ApprovalIn, EvidenceIn, ExperimentResultIn
from app.workflows import approval as approvals
from app.workflows.gates import latest_artifact
from app.workflows.orchestrator import Orchestrator
from app.workflows.phases import add_evidence, run_phase

router = APIRouter(prefix="/api/ventures/{venture_id}", tags=["phases"])

SUBJECT_ARTIFACT = {"commercial_setup": "commercial_pack", "launch_package": "launch_pack"}


@router.get("/phases")
def phases(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> list[dict[str, Any]]:
    return phases_view(db, venture)


@router.post("/phases/{phase}/run")
def run(phase: int, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    if phase not in range(1, 7):
        raise NotFound("Phases are numbered 1 to 6.")
    result = run_phase(orch, phase)
    orch.db.commit()
    return {"result": result, "phases": phases_view(orch.db, orch.venture), "venture": venture_view(orch.db, orch.venture)}


@router.post("/phases/{phase}/gate")
def gate(phase: int, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    if phase not in range(1, 7):
        raise NotFound("Phases are numbered 1 to 6.")
    decision = orch.evaluate_gate(phase)
    orch.db.commit()
    return {"gate": gate_view(decision), "venture": venture_view(orch.db, orch.venture)}


@router.post("/experiments/{experiment_id}/results", status_code=201)
def record_result(experiment_id: str, body: ExperimentResultIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    exp = orch.db.get(ValidationExperiment, experiment_id)
    if exp is None or exp.venture_id != orch.venture.id:
        raise NotFound("Experiment not found.")
    if orch.venture.state not in ("VALIDATING", "OPERATING"):
        raise InvalidTransition("Results can be recorded while validating or operating.")
    if body.source == "mocked" and orch.venture.mode != "demo":
        raise Forbidden("MOCKED results are only allowed in demo ventures. Record what actually happened.")
    result = ExperimentResult(experiment_id=exp.id, observed=body.observed, source=body.source, note=body.note,
                              evidence_url=str(body.evidence_url) if body.evidence_url else None)
    orch.db.add(result)
    orch.audit.record(orch.db, venture_id=orch.venture.id, agent="founder", action="record_experiment_result",
                      execution_mode="founder_action", sources=[str(body.evidence_url)] if body.evidence_url else [],
                      detail={"experiment": exp.name, "observed": body.observed, "target": exp.target, "source": body.source})
    orch.db.commit()
    return {"experiment_id": exp.id, "observed": body.observed, "target": exp.target, "source": body.source}


@router.post("/approvals", status_code=201)
def approve(body: ApprovalIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    subject_id = body.subject_id
    if body.subject_type in SUBJECT_ARTIFACT:
        artifact = latest_artifact(orch.db, orch.venture.id, SUBJECT_ARTIFACT[body.subject_type])
        if artifact is None:
            raise InvalidTransition(f"There is no {body.subject_type.replace('_', ' ')} to review yet.")
        subject_id = artifact.id
    if not subject_id:
        raise Forbidden("subject_id is required for this approval.")
    record = approvals.record_decision(orch.db, orch.venture, subject_type=body.subject_type, subject_id=subject_id,
                                       decision=body.decision, actor="founder", reason=body.reason, audit=orch.audit)
    orch.db.commit()
    return {"id": record.id, "subject_type": record.subject_type, "subject_id": record.subject_id, "decision": record.decision}


@router.get("/evidence")
def evidence(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> list[dict[str, Any]]:
    rows = db.scalars(select(EvidenceRecord).where(EvidenceRecord.venture_id == venture.id).order_by(EvidenceRecord.created_at))
    return [{"id": r.id, "claim": r.claim, "classification": r.classification, "source_url": r.source_url, "source_title": r.source_title,
             "published_at": r.published_at, "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
             "confidence": r.confidence, "limitations": r.limitations, "implication": r.implication,
             "research_question": r.research_question, "node_id": r.node_id, "verification_status": r.verification_status,
             "created_by": r.created_by} for r in rows]


@router.post("/evidence", status_code=201)
def add_founder_evidence(body: EvidenceIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    record = add_evidence(orch, claim=body.claim, classification=body.classification, verification_status="founder_supplied",
                          created_by="founder", retrieved_by_system=False,
                          source_url=str(body.source_url) if body.source_url else None, source_title=body.source_title,
                          node_id=body.node_id, limitations=body.limitations)
    orch.audit.record(orch.db, venture_id=orch.venture.id, agent="founder", action="add_evidence", execution_mode="founder_action",
                      sources=[record.source_url] if record.source_url else [], detail={"classification": record.classification})
    orch.db.commit()
    return {"id": record.id, "classification": record.classification, "verification_status": record.verification_status,
            "limitations": record.limitations}
