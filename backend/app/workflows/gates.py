"""Deterministic phase gates.

Every gate is plain code over recorded data: approvals, thresholds declared before results, test
exit codes, safety scans. The outcome is one of GO / REPEAT / PIVOT / STOP. The Gatekeeper agent can
explain an outcome afterwards but has no way to change it.

Outcome precedence: any hard-policy failure -> STOP; otherwise the gate's own rules below.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BusinessProposal,
    EvidenceRecord,
    GeneratedArtifact,
    MockOrder,
    SupportTicket,
    ValidationExperiment,
    Venture,
)
from app.schemas.common import GateOutcome
from app.schemas.founder import FounderProfileData
from app.services.mock_reconcile import reconcile
from app.services.safety import screen_generated_text, screen_venture_category
from app.workflows.approval import latest_decision

# Thresholds (declared here so they are visible and testable).
FOUNDER_FIT_MIN = 3
CAPITAL_STRETCH_FACTOR = 3.0
VALIDATION_REPEAT_RATIO = 0.5  # >= 50% of target: run the experiment again / longer
VALIDATION_PIVOT_RATIO = 0.25  # 25–50%: pivot; below 25%: stop
MAX_REFUND_RATE = 0.30
PAYMENT_PROVIDER_ENV_PREFIXES = ("STRIPE_", "PAYPAL_", "PAYMOB_", "FAWRY_", "BRAINTREE_", "ADYEN_")


@dataclass
class Check:
    id: str
    label: str
    passed: bool
    detail: str
    severity: str = "required"  # hard_policy | required | advisory

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "label": self.label, "passed": self.passed, "detail": self.detail, "severity": self.severity}


@dataclass
class GateResult:
    phase: int
    outcome: GateOutcome
    reasoning: str
    evidence_basis: str
    checks: list[Check] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


def latest_artifact(db: Session, venture_id: str, kind: str) -> GeneratedArtifact | None:
    return db.scalars(
        select(GeneratedArtifact)
        .where(GeneratedArtifact.venture_id == venture_id, GeneratedArtifact.kind == kind)
        .order_by(GeneratedArtifact.created_at.desc())
    ).first()


def approved_proposal(db: Session, venture_id: str) -> BusinessProposal | None:
    return db.scalars(
        select(BusinessProposal)
        .where(BusinessProposal.venture_id == venture_id, BusinessProposal.status == "approved")
        .order_by(BusinessProposal.number.desc())
    ).first()


def _hard_stop(checks: list[Check]) -> bool:
    return any(c.severity == "hard_policy" and not c.passed for c in checks)


def _failed(checks: list[Check], *ids: str) -> bool:
    return any(c.id in ids and not c.passed for c in checks)


# --- Phase 1: Discover ------------------------------------------------------------------------


def evaluate_discover(db: Session, venture: Venture, profile: FounderProfileData) -> GateResult:
    proposal = approved_proposal(db, venture.id)
    checks: list[Check] = [
        Check("approved_proposal", "Founder approved a business proposal", proposal is not None,
              "Approved proposal on record." if proposal else "No approved proposal.")
    ]
    if proposal is None:
        return GateResult(1, GateOutcome.REPEAT, "Approve a proposal before the Discover gate.", "none", checks)
    p = proposal.data
    category_text = " ".join([p["one_liner"], p["product_category"], p["solution"], p["business_name"]])
    category = screen_venture_category(category_text)
    checks.append(Check("allowed_category", "Product category is allowed (digital, not finance/crypto/health/legal)",
                        not category.blocked, "; ".join(f.message for f in category.findings) or "Allowed.", "hard_policy"))

    fit = int(p.get("founder_fit_score", 0))
    checks.append(Check("founder_fit", f"Founder–idea fit is at least {FOUNDER_FIT_MIN}/5 (heuristic)", fit >= FOUNDER_FIT_MIN,
                        f"Heuristic fit score {fit}/5 from the proposal."))

    budget = profile.resources.budget_amount
    capital = p.get("estimated_startup_capital") or {}
    amount, currency = capital.get("amount"), capital.get("currency")
    if budget is None or amount is None or currency != profile.resources.budget_currency:
        checks.append(Check("capital_vs_budget", "Start-up capital fits the founder's budget", True,
                            "Not comparable (missing figure or different currency) — recorded as UNKNOWN.", "advisory"))
        capital_ok, capital_detail = True, "unknown"
    else:
        ratio = amount / budget if budget else float("inf")
        capital_ok = ratio <= CAPITAL_STRETCH_FACTOR
        capital_detail = f"{amount:,.0f} {currency} needed vs {budget:,.0f} budget ({ratio:.1f}× budget, {capital.get('classification', 'ASSUMPTION')})."
        checks.append(Check("capital_vs_budget", f"Start-up capital is within {CAPITAL_STRETCH_FACTOR:g}× the budget", capital_ok, capital_detail))

    checks.append(Check("recommendation", "Mate's own proposal does not advise against proceeding",
                        p.get("recommendation") != "DO_NOT_PROCEED", f"Proposal recommendation: {p.get('recommendation')}."))
    experiment = p.get("first_experiment") or {}
    checks.append(Check("experiment_defined", "A first validation experiment with a target is declared",
                        bool(experiment.get("target")) and bool(experiment.get("window_days")),
                        f"{experiment.get('metric', '?')}: target {experiment.get('target')} in {experiment.get('window_days')} days."))
    evidence_count = len(list(db.scalars(select(EvidenceRecord.id).where(EvidenceRecord.venture_id == venture.id))))
    research = latest_artifact(db, venture.id, "evidence_register")
    checks.append(Check("evidence_register", "Research ran and the evidence register exists", research is not None and evidence_count > 0,
                        f"{evidence_count} evidence records." if research else "Run Phase 1 research first."))
    interviews = latest_artifact(db, venture.id, "interview_plan")
    checks.append(Check("interview_plan", "Mom Test interview plan prepared", interviews is not None,
                        "Ready." if interviews else "Run Phase 1 to prepare interview questions."))
    checks.append(Check("differentiation", "At least one alternative and a value proposition are named",
                        bool(p.get("competitive_alternatives")) and bool(p.get("value_proposition")),
                        f"{len(p.get('competitive_alternatives') or [])} alternatives named.", "advisory"))

    if _hard_stop(checks):
        outcome, why = GateOutcome.STOP, "A hard policy rule failed; this venture cannot continue in Mate."
    elif _failed(checks, "evidence_register", "interview_plan"):
        outcome, why = GateOutcome.REPEAT, "Phase 1 work is incomplete; run research and interview planning, then re-check."
    elif not capital_ok and (fit < FOUNDER_FIT_MIN or p.get("recommendation") == "DO_NOT_PROCEED"):
        outcome, why = GateOutcome.STOP, ("The required capital is far beyond the budget and the fit or the evidence is weak. "
                                          "Mate recommends stopping this direction rather than spending to find out.")
    elif _failed(checks, "capital_vs_budget", "founder_fit", "recommendation"):
        outcome, why = GateOutcome.PIVOT, "The direction does not fit the founder's resources or evidence; rework it before validating."
    elif _failed(checks, "experiment_defined"):
        outcome, why = GateOutcome.REPEAT, "Declare a measurable first experiment before moving on."
    else:
        outcome, why = GateOutcome.GO, "The direction fits the founder well enough to justify validation. Nothing is validated yet."
    return GateResult(1, outcome, why, "founder_and_assumptions", checks, {"capital": capital_detail, "fit": fit})


# --- Phase 2: Validate ------------------------------------------------------------------------


def experiment_progress(experiment: ValidationExperiment) -> tuple[float | None, str]:
    if not experiment.results:
        return None, "none"
    latest = experiment.results[-1]
    return latest.observed / experiment.target if experiment.target else None, latest.source


def evaluate_validate(db: Session, venture: Venture) -> GateResult:
    pack = latest_artifact(db, venture.id, "validation_pack")
    experiments = list(db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == venture.id)
                                  .order_by(ValidationExperiment.created_at)))
    checks = [
        Check("validation_pack", "Lean Canvas, riskiest assumptions and landing-page draft exist", pack is not None,
              "Ready." if pack else "Run Phase 2 first."),
        Check("experiments_declared", "Experiment targets were declared and locked before results", bool(experiments) and all(e.locked_at for e in experiments),
              f"{len(experiments)} experiment(s), targets locked." if experiments else "No experiments."),
    ]
    sources: set[str] = set()
    ratios: list[tuple[ValidationExperiment, float]] = []
    for exp in experiments:
        ratio, source = experiment_progress(exp)
        if ratio is None:
            checks.append(Check(f"result_{exp.id}", f"{exp.name}: result recorded", False,
                                f"Target {exp.target:g} {exp.metric} in {exp.window_days} days — no result recorded yet (pending)."))
            continue
        sources.add(source)
        observed = exp.results[-1].observed
        ratios.append((exp, ratio))
        label = " (MOCKED demo input)" if source == "mocked" else " (founder-reported)"
        checks.append(Check(f"result_{exp.id}", f"{exp.name}: target met", ratio >= 1.0,
                            f"{observed:g} of {exp.target:g} {exp.metric} = {ratio:.0%} of target{label}. "
                            + ("Target met." if ratio >= 1 else "Target missed.")))
    basis = "mocked" if sources == {"mocked"} else ("mixed" if "mocked" in sources else ("founder_reported" if sources else "none"))

    primary = experiments[0] if experiments else None
    primary_ratio = next((r for e, r in ratios if primary and e.id == primary.id), None)
    if pack is None or not experiments:
        outcome, why = GateOutcome.REPEAT, "Validation is not set up yet."
    elif primary_ratio is None:
        outcome, why = GateOutcome.REPEAT, "Validation is pending: no result recorded for the primary experiment. Nothing is assumed."
    else:
        worst = min(r for _, r in ratios)
        if worst >= 1.0:
            outcome, why = GateOutcome.GO, "Every recorded experiment met the target declared in advance."
        elif worst >= VALIDATION_REPEAT_RATIO:
            outcome, why = GateOutcome.REPEAT, "Results came close but missed the target. Repeat or extend the experiment; do not round up."
        elif worst >= VALIDATION_PIVOT_RATIO:
            outcome, why = GateOutcome.PIVOT, "Results were well below target. Change the customer, problem or offer before building."
        else:
            outcome, why = GateOutcome.STOP, "Results were far below the target declared in advance. Mate recommends stopping rather than spinning the result."
    if basis == "mocked":
        why += " Basis: MOCKED demo inputs — this shows the rule, not your market."
    return GateResult(2, outcome, why, basis, checks, {"ratios": {e.name: round(r, 3) for e, r in ratios}})


# --- Phase 3: Build ---------------------------------------------------------------------------


def evaluate_build(db: Session, venture: Venture) -> GateResult:
    spec = latest_artifact(db, venture.id, "product_spec")
    report = latest_artifact(db, venture.id, "mvp_test_report")
    meta = report.meta if report else {}
    checks = [
        Check("spec", "Product spec with acceptance criteria exists", spec is not None, "Ready." if spec else "Run Phase 3."),
        Check("files", "MVP files generated (UI, logic, tests, README)", bool(meta.get("files_complete")),
              ", ".join(meta.get("files", [])) or "No build yet."),
        Check("tests_executed", "Generated tests were executed", bool(meta.get("tests_executed")),
              meta.get("runner_note") or ("Executed." if meta.get("tests_executed") else "Not executed.")),
        Check("tests_pass", "All generated tests pass", meta.get("tests_failed") == 0 and (meta.get("tests_passed") or 0) > 0 and meta.get("exit_code") == 0,
              f"{meta.get('tests_passed', 0)} passed, {meta.get('tests_failed', 0)} failed, exit code {meta.get('exit_code')}."),
        Check("scope", "Every must-have feature maps to a supported capability", not meta.get("unsupported_capabilities"),
              "All supported." if not meta.get("unsupported_capabilities") else "Unsupported: " + ", ".join(meta["unsupported_capabilities"])),
    ]
    if all(c.passed for c in checks):
        outcome, why = GateOutcome.GO, "The MVP builds, its tests pass and it matches the agreed scope."
    else:
        outcome, why = GateOutcome.REPEAT, "The MVP is not ready: fix the failed checks and rebuild."
    return GateResult(3, outcome, why, "test_results", checks, {k: meta.get(k) for k in ("tests_passed", "tests_failed")})


# --- Phase 4: Commercial setup ----------------------------------------------------------------


def evaluate_commercial(db: Session, venture: Venture) -> GateResult:
    pack = latest_artifact(db, venture.id, "commercial_pack")
    break_even = latest_artifact(db, venture.id, "break_even")
    policies = [latest_artifact(db, venture.id, f"policy_{name}") for name in ("terms", "privacy", "refunds")]
    approval = latest_decision(db, venture.id, "commercial_setup", pack.id if pack else None) if pack else None
    be = break_even.meta if break_even else {}
    text = " ".join(p.content for p in policies if p) + (" " + pack.content if pack else "")
    unsafe = screen_generated_text(text)
    checks = [
        Check("pack", "Pricing, costs and checklist exist", pack is not None, "Ready." if pack else "Run Phase 4."),
        Check("unit_economics", "Price covers variable cost per sale (break-even computable)", bool(be.get("viable")),
              be.get("reason") or (f"Break-even at {be.get('break_even_units')} {be.get('break_even_unit_label')} (PROJECTION)." if be else "No calculation.")),
        Check("policies", "Draft terms, privacy and refund policies exist and are labelled DRAFT",
              all(p is not None and "DRAFT" in p.content and "not legal advice" in p.content for p in policies),
              "All three drafted and labelled." if all(policies) else "Missing policy drafts."),
        Check("no_unsafe_claims", "No income promises or manipulative claims", not unsafe.blocked,
              "; ".join(f.matched for f in unsafe.findings) or "Clean.", "hard_policy"),
        Check("no_payments", "No payment integration is configured", True, "Payments are MOCKED in code; no provider exists.", "hard_policy"),
        Check("founder_approval", "Founder reviewed and approved the commercial setup",
              approval is not None and approval.decision == "approve",
              "Approved by founder." if approval and approval.decision == "approve"
              else ("Rejected by founder — revise and resubmit." if approval else "Awaiting founder review.")),
    ]
    if _hard_stop(checks):
        outcome, why = GateOutcome.STOP, "A hard policy rule failed."
    elif _failed(checks, "unit_economics") and pack is not None:
        outcome, why = GateOutcome.PIVOT, "At the proposed price every sale loses money. Rework pricing or costs."
    elif not all(c.passed for c in checks):
        outcome, why = GateOutcome.REPEAT, "Commercial setup is incomplete or not yet approved by the founder."
    else:
        outcome, why = GateOutcome.GO, "Pricing and draft policies are approved by the founder. Policies still need legal review."
    return GateResult(4, outcome, why, "assumptions_and_approval", checks, {"break_even": be})


# --- Phase 5: Launch (MOCKED commerce) ---------------------------------------------------------


def payment_env_vars() -> list[str]:
    return sorted(k for k in os.environ if k.upper().startswith(PAYMENT_PROVIDER_ENV_PREFIXES))


def evaluate_launch(db: Session, venture: Venture) -> GateResult:
    pack = latest_artifact(db, venture.id, "launch_pack")
    approval = latest_decision(db, venture.id, "launch_package", pack.id if pack else None) if pack else None
    recon = reconcile(db, venture.id)
    orders = recon["orders"]
    delivered = [o for o in orders if o["access"] in ("active", "revoked")]
    refunded_and_revoked = [o for o in orders if o["status"] == "mock_refunded" and o["access"] == "revoked"]
    dup_test = latest_artifact(db, venture.id, "mock_idempotency_check")
    unsafe = screen_generated_text(pack.content if pack else "")
    provider_vars = payment_env_vars()
    checks = [
        Check("pack", "Store page, announcements and checklist drafted", pack is not None, "Ready." if pack else "Run Phase 5."),
        Check("no_unsafe_claims", "Launch copy has no fake reviews, urgency or income claims", not unsafe.blocked,
              "; ".join(f.matched for f in unsafe.findings) or "Clean.", "hard_policy"),
        Check("no_payment_credentials", "No payment-provider credentials present in the environment", not provider_vars,
              "None found." if not provider_vars else "Found: " + ", ".join(provider_vars), "hard_policy"),
        Check("founder_approval", "Founder approved the launch package", approval is not None and approval.decision == "approve",
              "Approved." if approval and approval.decision == "approve" else "Awaiting founder approval."),
        Check("mock_delivery", "A MOCKED purchase triggered MOCKED delivery", bool(delivered), f"{len(delivered)} mock order(s) delivered."),
        Check("mock_refund_revokes", "A MOCKED refund revoked access", bool(refunded_and_revoked), f"{len(refunded_and_revoked)} refunded with access revoked."),
        Check("idempotency", "Replaying a delivery event did not create a second entitlement",
              bool(dup_test and dup_test.meta.get("passed")), "Verified." if dup_test and dup_test.meta.get("passed") else "Not verified yet."),
        Check("reconciliation", "MOCKED ledger reconciles with orders and access", recon["balanced"] and bool(orders),
              "Balanced." if recon["balanced"] and orders else "; ".join(recon["mismatches"]) or "No mock orders yet."),
    ]
    if _hard_stop(checks):
        outcome, why = GateOutcome.STOP, "A hard safety rule failed; the launch package cannot proceed."
    elif all(c.passed for c in checks):
        outcome, why = GateOutcome.GO, "The launch package is approved and the MOCKED sale-to-delivery-to-refund cycle works."
    else:
        outcome, why = GateOutcome.REPEAT, "Finish the launch package, approval and the MOCKED commerce checks."
    return GateResult(5, outcome, why, "mocked", checks, {"reconciliation_totals": recon["totals"]})


# --- Phase 6: Operate and learn ---------------------------------------------------------------


def operating_metrics(db: Session, venture: Venture) -> dict[str, Any]:
    experiments = list(db.scalars(select(ValidationExperiment).where(ValidationExperiment.venture_id == venture.id)))
    orders = list(db.scalars(select(MockOrder).where(MockOrder.venture_id == venture.id)))
    tickets = list(db.scalars(select(SupportTicket).where(SupportTicket.venture_id == venture.id)))
    results = []
    for exp in experiments:
        ratio, source = experiment_progress(exp)
        results.append({"experiment": exp.name, "target": exp.target, "metric": exp.metric,
                        "observed": exp.results[-1].observed if exp.results else None,
                        "ratio": round(ratio, 3) if ratio is not None else None, "source": source})
    refunded = sum(1 for o in orders if o.status == "mock_refunded")
    return {
        "experiments": results,
        "mock_orders": len(orders),
        "mock_refunds": refunded,
        "mock_refund_rate": round(refunded / len(orders), 3) if orders else None,
        "support_tickets": len(tickets),
        "support_ticket_sources": sorted({t.source for t in tickets}),
        "orders_label": "MOCKED",
    }


def evaluate_operate(db: Session, venture: Venture) -> GateResult:
    metrics = operating_metrics(db, venture)
    memo = latest_artifact(db, venture.id, "operations_review")
    ratios = [r["ratio"] for r in metrics["experiments"] if r["ratio"] is not None]
    sources = {r["source"] for r in metrics["experiments"] if r["ratio"] is not None} | set(metrics["support_ticket_sources"])
    real_data = bool(sources - {"mocked", "none"})
    refund_rate = metrics["mock_refund_rate"]
    checks = [
        Check("memo", "Persevere-or-pivot memo written", memo is not None, "Ready." if memo else "Run Phase 6."),
        Check("experiment_results", "Experiment results available", bool(ratios), f"{len(ratios)} experiment(s) with results."),
        Check("experiments_on_target", "Experiments are at or above target", bool(ratios) and min(ratios) >= 1.0,
              ", ".join(f"{r:.0%}" for r in ratios) or "None."),
        Check("refund_rate", f"Refund rate at or below {MAX_REFUND_RATE:.0%} (needs 3+ orders)",
              refund_rate is None or metrics["mock_orders"] < 3 or refund_rate <= MAX_REFUND_RATE,
              f"{refund_rate:.0%} of {metrics['mock_orders']} MOCKED orders." if refund_rate is not None else "No orders."),
        Check("real_customer_data", "Some metrics come from real customers (not MOCKED)", real_data,
              "Founder-reported data present." if real_data else "All metrics are MOCKED or missing.", "advisory"),
    ]
    if memo is None or not ratios:
        outcome, why = GateOutcome.REPEAT, "Not enough information to decide; collect results and write the memo."
    elif min(ratios) < VALIDATION_PIVOT_RATIO:
        outcome, why = GateOutcome.STOP, "Results are far below target. Mate recommends stopping."
    elif min(ratios) < 1.0 or _failed(checks, "refund_rate"):
        outcome, why = GateOutcome.PIVOT, "Results or refunds point to a mismatch between offer and customer."
    else:
        outcome, why = GateOutcome.GO, "Continue: the recorded results support persevering with the next experiment."
    if not real_data:
        if venture.mode != "demo" and outcome == GateOutcome.GO:
            outcome, why = GateOutcome.REPEAT, "Only MOCKED data exists; collect real customer data before deciding to continue."
        else:
            why += " Basis: MOCKED demo data — not evidence about real customers."
    return GateResult(6, outcome, why, "mocked" if not real_data else "mixed", checks, metrics)


def evaluate(db: Session, venture: Venture, phase: int, profile: FounderProfileData) -> GateResult:
    if phase == 1:
        return evaluate_discover(db, venture, profile)
    evaluators = {2: evaluate_validate, 3: evaluate_build, 4: evaluate_commercial, 5: evaluate_launch, 6: evaluate_operate}
    return evaluators[phase](db, venture)
