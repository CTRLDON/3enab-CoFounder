"""Phase runners: what each phase's agents do before its gate is evaluated."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.agents.commercial import CommercialAgent, render_policies
from app.agents.launch import LaunchAgent
from app.agents.market_research import MarketResearchAgent
from app.agents.mvp_builder import MvpBuilderAgent
from app.agents.operations import OperationsAgent
from app.agents.product_architect import ProductArchitectAgent
from app.agents.validation import ValidationAgent
from app.config import get_settings
from app.errors import InvalidTransition
from app.models import EvidenceRecord, Hypothesis, SupportTicket, ValidationExperiment, utcnow
from app.schemas.agent_io import CommercialPack, ExperimentDraft, ProductSpec
from app.schemas.common import Confidence, EvidenceClass
from app.services import plan_versioning, renderers
from app.services.finance import break_even
from app.services.mvp_template import bundle_preview
from app.services.research_service import ResearchService, normalize_classification
from app.workflows.gates import approved_proposal, latest_artifact, operating_metrics
from app.workflows.orchestrator import Orchestrator
from app.workflows.state_machine import PHASE_STATE

_research_service: ResearchService | None = None


def research_service() -> ResearchService:
    global _research_service
    if _research_service is None:
        _research_service = ResearchService(get_settings())
    return _research_service


def set_research_service(service: ResearchService | None) -> None:
    global _research_service
    _research_service = service


def _plan_document(orch: Orchestrator) -> dict[str, Any]:
    plan = plan_versioning.get_plan(orch.db, orch.venture.id)
    if plan is None:
        raise InvalidTransition("Approve a proposal first.")
    return plan_versioning.get_version(orch.db, plan).data


def add_evidence(orch: Orchestrator, *, claim: str, classification: EvidenceClass, verification_status: str, created_by: str,
                 retrieved_by_system: bool, **fields: Any) -> EvidenceRecord:
    allowed, note = normalize_classification(classification, source_url=fields.get("source_url"),
                                             retrieved_by_system=retrieved_by_system, venture_mode=orch.venture.mode)
    limitations = fields.pop("limitations", "") or ""
    if note:
        limitations = (limitations + " " + note).strip()
        verification_status = "downgraded"
    record = EvidenceRecord(venture_id=orch.venture.id, claim=claim[:2000], classification=allowed.value,
                            verification_status=verification_status, created_by=created_by, limitations=limitations, **fields)
    orch.db.add(record)
    orch.db.flush()
    return record


def run_phase(orch: Orchestrator, phase: int) -> dict[str, Any]:
    orch.require_state({PHASE_STATE[phase]}, f"run phase {phase}")
    runner = {1: _discover, 2: _validate, 3: _build, 4: _commercial, 5: _launch, 6: _operate}[phase]
    return runner(orch)


# --- Phase 1 -----------------------------------------------------------------------------------------


def _discover(orch: Orchestrator) -> dict[str, Any]:
    proposal = approved_proposal(orch.db, orch.venture.id)
    assert proposal is not None
    public = {k: v for k, v in proposal.data.items() if not k.startswith("_")}
    country = orch.profile().preferences.target_country
    _, outcome = MarketResearchAgent().research(orch.ctx, research_service(), proposal=public, country=country)
    records = []
    for draft in outcome.evidence:
        records.append(add_evidence(
            orch, claim=draft.claim, classification=draft.classification, verification_status=draft.verification_status,
            created_by="market_research", retrieved_by_system=draft.retrieved_at is not None,
            source_url=draft.source_url, source_title=draft.source_title, published_at=draft.published_at,
            retrieved_at=draft.retrieved_at, confidence=draft.confidence.value, limitations=draft.limitations,
            implication=draft.implication, research_question=draft.research_question, node_id=draft.node_id,
        ))
    for missing in public.get("missing_evidence", []):
        records.append(add_evidence(orch, claim=missing, classification=EvidenceClass.UNKNOWN, verification_status="missing_evidence",
                                    created_by="skeptical_cofounder", retrieved_by_system=False,
                                    limitations="Listed as missing evidence in the approved proposal.", confidence=Confidence.LOW.value))
    register = orch.save_artifact(1, "evidence_register", "Evidence register", "markdown",
                                  renderers.evidence_register_md(records, outcome.notes, outcome.suggested_sources),
                                  ["DEGRADED RESEARCH"] if not outcome.retrieval_available or not get_settings().research_online else [],
                                  {"retrieval_available": outcome.retrieval_available, "notes": outcome.notes,
                                   "suggested_sources": outcome.suggested_sources})
    interviews = ValidationAgent().interview_plan(orch.ctx, proposal=public)
    orch.save_artifact(1, "interview_plan", "Customer interview plan (Mom Test)", "markdown",
                       renderers.interview_md(interviews.model_dump()), [], interviews.model_dump(mode="json"))
    return {"evidence_records": len(records), "retrieval_available": outcome.retrieval_available, "register_id": register.id}


# --- Phase 2 -----------------------------------------------------------------------------------------


def _register_summary(orch: Orchestrator) -> str:
    rows = orch.db.scalars(select(EvidenceRecord).where(EvidenceRecord.venture_id == orch.venture.id))
    return "\n".join(f"- [{r.classification}] {r.claim[:200]}" for r in rows) or "- (empty)"


def _create_experiment(orch: Orchestrator, draft: ExperimentDraft, hypothesis_id: str | None) -> ValidationExperiment:
    exp = ValidationExperiment(venture_id=orch.venture.id, hypothesis_id=hypothesis_id, name=draft.name, method=draft.method,
                               metric=draft.metric, target=draft.target, window_days=draft.window_days, status="running",
                               locked_at=utcnow())
    orch.db.add(exp)
    orch.db.flush()
    orch.audit.record(orch.db, venture_id=orch.venture.id, agent="validation", action="declare_experiment_target",
                      execution_mode="deterministic_rule",
                      detail={"experiment": draft.name, "target": draft.target, "window_days": draft.window_days})
    return exp


def _validate(orch: Orchestrator) -> dict[str, Any]:
    document = _plan_document(orch)
    pack = ValidationAgent().validation_pack(orch.ctx, plan_document=document, evidence_summary=_register_summary(orch))
    existing = list(orch.db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == orch.venture.id)))
    if not orch.db.scalars(select(Hypothesis).where(Hypothesis.venture_id == orch.venture.id)).first():
        for item in pack.riskiest_assumptions:
            orch.db.add(Hypothesis(venture_id=orch.venture.id, statement=item.statement, risk=item.risk, node_id=item.node_id))
        orch.db.flush()
    if not existing:  # targets are declared once and locked; re-runs never move the goalposts
        proposal = approved_proposal(orch.db, orch.venture.id)
        assert proposal is not None
        first_hypothesis = orch.db.scalars(select(Hypothesis).where(Hypothesis.venture_id == orch.venture.id)).first()
        _create_experiment(orch, ExperimentDraft.model_validate(proposal.data["first_experiment"]), first_hypothesis.id if first_hypothesis else None)
        for extra in pack.extra_experiments:
            _create_experiment(orch, extra, None)
    canvas = pack.lean_canvas.model_dump()
    orch.save_artifact(2, "lean_canvas", "Lean Canvas", "markdown",
                       renderers.lean_canvas_md(canvas, [r.model_dump() for r in pack.riskiest_assumptions]), ["ASSUMPTIONS"], canvas)
    orch.save_artifact(2, "landing_page", "Landing page draft (not published)", "html",
                       renderers.landing_page_html(pack.landing_page.model_dump()), ["DRAFT", "NOT PUBLISHED"])
    orch.save_artifact(2, "validation_pack", "Validation pack", "json", pack.model_dump_json(indent=2), [], {})
    experiments = list(orch.db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == orch.venture.id)))
    return {"experiments": [{"id": e.id, "name": e.name, "target": e.target, "metric": e.metric, "window_days": e.window_days} for e in experiments]}


# --- Phase 3 -----------------------------------------------------------------------------------------


def _validation_summary(orch: Orchestrator) -> str:
    lines = []
    for exp in orch.db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == orch.venture.id)):
        latest = exp.results[-1] if exp.results else None
        lines.append(f"- {exp.name}: target {exp.target:g} {exp.metric}; observed "
                     + (f"{latest.observed:g} ({latest.source})" if latest else "nothing yet"))
    return "\n".join(lines) or "- no experiments"


def _build(orch: Orchestrator) -> dict[str, Any]:
    document = _plan_document(orch)
    spec = ProductArchitectAgent().specify(orch.ctx, plan_document=document, validation_summary=_validation_summary(orch))
    orch.save_artifact(3, "product_spec", f"Product specification — {spec.product_name}", "json", spec.model_dump_json(indent=2), [], {})
    builder = MvpBuilderAgent()
    copy = builder.write_copy(orch.ctx, spec=spec)
    accent = orch.theme()["tokens"]["accent"]
    result = builder.build(orch.ctx, spec=spec, copy=copy, accent=accent)

    out_dir = get_settings().artifacts_dir / orch.venture.id / f"mvp-{utcnow().strftime('%Y%m%d%H%M%S')}"
    for name, content in result.files.items():
        target = out_dir / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    required = {"index.html", "app.js", "app-core.js", "styles.css", "README.md", "tests/core.test.js", "config.json"}
    bundle = orch.save_artifact(3, "mvp_bundle", f"MVP starter — {copy.app_title}", "bundle", json.dumps(result.files),
                                ["GENERATED FROM TEMPLATE"], {"path": str(out_dir), "files": sorted(result.files)})
    report_meta = {
        "files": sorted(result.files), "files_complete": required <= set(result.files),
        "tests_executed": result.test_executed, "tests_passed": result.tests_passed, "tests_failed": result.tests_failed,
        "exit_code": result.exit_code, "unsupported_capabilities": result.unsupported_capabilities,
        "runner_note": None if result.test_executed else result.output_tail, "bundle_id": bundle.id,
    }
    report_md = (f"# MVP build report — {copy.app_title}\n\n"
                 f"- Files: {', '.join(sorted(result.files))}\n- Tests executed: {result.test_executed}\n"
                 f"- Passed: {result.tests_passed} · Failed: {result.tests_failed} · Exit code: {result.exit_code}\n\n"
                 f"```text\n{result.output_tail[-1800:]}\n```\n")
    orch.save_artifact(3, "mvp_test_report", "MVP test report", "markdown", report_md, [], report_meta)
    orch.save_artifact(3, "mvp_preview", "MVP preview", "html", bundle_preview(result.files), ["GENERATED FROM TEMPLATE"])
    return {"tests_passed": result.tests_passed, "tests_failed": result.tests_failed, "bundle_id": bundle.id}


# --- Phase 4 -----------------------------------------------------------------------------------------


def _commercial(orch: Orchestrator) -> dict[str, Any]:
    document = _plan_document(orch)
    spec_artifact = latest_artifact(orch.db, orch.venture.id, "product_spec")
    spec = ProductSpec.model_validate_json(spec_artifact.content) if spec_artifact else None
    profile = orch.profile()
    budget = f"{profile.resources.budget_amount or 'unknown'} {profile.resources.budget_currency}"
    pack = CommercialAgent().propose(orch.ctx, plan_document=document,
                                     spec_summary=spec.problem_statement if spec else "not specified",
                                     budget=budget, currency=profile.resources.budget_currency)
    artifact = orch.save_artifact(4, "commercial_pack", "Pricing, costs and compliance checklist", "json",
                                  pack.model_dump_json(indent=2), ["ASSUMPTIONS", "AWAITING FOUNDER APPROVAL"], {})
    result = break_even(pack)
    orch.save_artifact(4, "break_even", "Break-even scenarios (PROJECTION)", "json", json.dumps(result, indent=2), ["PROJECTION"], result)
    product_name = spec.product_name if spec else document["title"]
    for name, text in render_policies(pack, product_name).items():
        orch.save_artifact(4, f"policy_{name}", f"Draft {name.replace('_', ' ')} policy", "markdown", text, ["DRAFT", "NOT LEGAL ADVICE"])
    return {"commercial_pack_id": artifact.id, "break_even": result}


# --- Phase 5 -----------------------------------------------------------------------------------------


def _launch(orch: Orchestrator) -> dict[str, Any]:
    document = _plan_document(orch)
    commercial = latest_artifact(orch.db, orch.venture.id, "commercial_pack")
    pack_c = CommercialPack.model_validate_json(commercial.content) if commercial else None
    paid = next((t for t in (pack_c.tiers if pack_c else []) if t.price > 0), None)
    price_line = f"{paid.name}: {paid.price:,.0f} {paid.currency} ({paid.period.replace('_', ' ')})" if paid else "Price not set"
    pack = LaunchAgent().prepare(orch.ctx, plan_document=document, pricing=price_line)
    artifact = orch.save_artifact(5, "launch_pack", "Launch package", "json", pack.model_dump_json(indent=2),
                                  ["DRAFT", "NOT PUBLISHED", "AWAITING FOUNDER APPROVAL"], {})
    orch.save_artifact(5, "store_page", "Store page (MOCKED, not published)", "html",
                       renderers.store_page_html(pack.model_dump(), price_line), ["MOCKED", "NOT PUBLISHED"])
    return {"launch_pack_id": artifact.id, "price_line": price_line}


# --- Phase 6 -----------------------------------------------------------------------------------------


def _operate(orch: Orchestrator) -> dict[str, Any]:
    metrics = operating_metrics(orch.db, orch.venture)
    lines = [f"- Experiment '{r['experiment']}': observed {r['observed']} vs target {r['target']} ({r['source']})" for r in metrics["experiments"]]
    lines += [f"- MOCKED orders: {metrics['mock_orders']}, MOCKED refunds: {metrics['mock_refunds']}",
              f"- Support tickets: {metrics['support_tickets']} (sources: {', '.join(metrics['support_ticket_sources']) or 'none'})"]
    review = OperationsAgent().review(orch.ctx, metrics_summary="\n".join(lines))
    memo = review.memo
    memo_md = (f"# Persevere-or-pivot memo\n\n**Operations agent recommendation: {memo.recommendation.replace('_', ' ')}** "
               "(advisory — the Phase 6 gate decides from recorded data)\n\n"
               f"{memo.summary}\n\n## What we learned\n{renderers.bullet(memo.what_we_learned)}\n\n"
               f"## Evidence gaps\n{renderers.bullet(memo.evidence_gaps)}\n\n## Next experiments\n{renderers.bullet(memo.next_experiments)}\n")
    orch.save_artifact(6, "operations_review", "Persevere-or-pivot memo", "markdown", memo_md,
                       ["MOCKED DATA BASIS"] if orch.venture.mode == "demo" else [], review.model_dump(mode="json"))
    orch.save_artifact(6, "metrics", "Metrics snapshot", "json", json.dumps(metrics, indent=2), ["MOCKED"] if orch.venture.mode == "demo" else [], metrics)
    return {"metrics": metrics, "recommendation": memo.recommendation}


def triage_ticket(orch: Orchestrator, ticket: SupportTicket) -> SupportTicket:
    review = latest_artifact(orch.db, orch.venture.id, "operations_review")
    categories = (review.meta.get("support_categories") if review else None) or ["Setup help", "Bug report", "Feature request", "Other"]
    triage = OperationsAgent().triage(orch.ctx, subject=ticket.subject, body=ticket.body, categories=categories)
    ticket.category, ticket.draft_reply, ticket.status = triage.category, triage.draft_reply, "draft_reply_awaiting_founder"
    return ticket
