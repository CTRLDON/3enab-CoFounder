"""Builds the first structured business plan from an approved proposal.

The plan is data (a list of nodes with stable ids) and drives the mind map. Node ids never change
between versions, so evidence, revisions and dependencies stay attached to the same node.
"""

from __future__ import annotations

from typing import Any

from app.schemas.agent_io import PlanNodeModel, ProposalDraft
from app.schemas.common import EconomicClass, EvidenceClass, MoneyEstimate

E = EconomicClass

# (id, title, category, economic class, phase, objective)
MAIN_SECTIONS: list[tuple[str, str, str, EconomicClass, int, str]] = [
    ("strategy", "Business strategy", "strategy", E.STRATEGIC, 1, "Decide what to test first and what to ignore for now."),
    ("market", "Target market", "market", E.STRATEGIC, 1, "Name one reachable customer group precisely."),
    ("problems", "Customer problems", "problems", E.STRATEGIC, 1, "Confirm the problem is painful enough to act on."),
    ("competitors", "Competitors and alternatives", "competitors", E.STRATEGIC, 1, "Know what customers use today and why they would switch."),
    ("value", "Value proposition", "value", E.STRATEGIC, 2, "State the single reason a customer chooses this."),
    ("risks", "Risks and validation", "risks", E.STRATEGIC, 2, "Test the riskiest assumption before building."),
    ("product", "Product and features", "product", E.EXPENSE, 3, "Ship the smallest product that tests the value proposition."),
    ("revenue", "Revenue model", "revenue", E.REVENUE, 4, "Define who pays, how much and how often."),
    ("costs", "Costs and resources", "costs", E.EXPENSE, 4, "Keep spending inside the founder's budget."),
    ("marketing", "Marketing and distribution", "marketing", E.MIXED, 5, "Find a repeatable way to reach the first customers."),
    ("launch", "Launch and growth", "launch", E.MIXED, 5, "Put the product in front of real customers, with approval at each step."),
    ("operations", "Operations and technology", "operations", E.EXPENSE, 6, "Support customers and measure what happens."),
]


def _node(**kwargs: Any) -> dict[str, Any]:
    return PlanNodeModel(**kwargs).model_dump(mode="json")


def build_initial_plan(proposal: ProposalDraft, *, country: str, currency: str) -> dict[str, Any]:
    p = proposal
    nodes: list[dict[str, Any]] = [
        _node(
            id="venture",
            title=p.business_name,
            category="venture",
            economic_class=E.STRATEGIC,
            summary=p.one_liner,
            objective=p.recommended_next_action,
            explanation=p.solution,
            main_assumption=p.missing_evidence[0] if p.missing_evidence else "",
            evidence_gap="; ".join(p.missing_evidence[:3]),
            risks=p.major_risks[:4],
            next_actions=[p.recommended_next_action],
        )
    ]
    texts = {
        "strategy": (p.recommended_next_action, p.founder_fit, "\n".join(p.reasons_for)),
        "market": (p.target_customer, f"Target market: {country or 'not specified'}.", p.target_customer),
        "problems": (p.problem, p.problem, "Interview customers before treating this problem as confirmed."),
        "competitors": (
            ", ".join(c.name for c in p.competitive_alternatives) or "Not yet identified",
            "Alternatives the founder's customers could use instead.",
            "Position against the status quo, not only against named products.",
        ),
        "value": (p.value_proposition, p.value_proposition, p.value_proposition),
        "risks": ("; ".join(p.major_risks[:2]), "Main risks identified during the debate.", p.first_experiment.method),
        "product": (p.solution, p.solution, "Build only what the first experiment needs."),
        "revenue": (p.business_model, p.business_model, "; ".join(p.revenue_streams)),
        "costs": (
            f"Estimated start-up capital: {p.estimated_startup_capital.amount or 'unknown'} {p.estimated_startup_capital.currency}",
            "Expected costs to reach a testable MVP and first sales.",
            "Prefer free tools and time over cash until demand is validated.",
        ),
        "marketing": ("Channels to be confirmed by validation.", "How the first customers will hear about the product.", "Start with channels the founder already has access to."),
        "launch": ("Launch only after the validation and build gates pass.", "A staged launch with founder approval at each step.", "All publishing and checkout are MOCKED in this build."),
        "operations": ("Support, delivery and metrics.", "Keep operations manual and simple until volume justifies tooling.", "Track the few metrics that decide persevere vs pivot."),
    }
    for node_id, title, category, econ, phase, objective in MAIN_SECTIONS:
        summary, explanation, strategy = texts[node_id]
        nodes.append(
            _node(
                id=node_id,
                parent_id="venture",
                title=title,
                category=category,
                economic_class=econ,
                summary=summary[:400],
                objective=objective,
                explanation=explanation,
                strategy=strategy,
                phase=phase,
            )
        )

    def child(node_id: str, parent: str, title: str, econ: EconomicClass, **extra: Any) -> None:
        parent_phase = next(n["phase"] for n in nodes if n["id"] == parent)
        nodes.append(_node(id=node_id, parent_id=parent, title=title[:80], category=parent, economic_class=econ, phase=parent_phase, **extra))

    child("founder-fit", "strategy", "Founder fit", E.STRATEGIC, summary=p.founder_fit, main_assumption="Founder can reach and serve this customer.")
    child("next-action", "strategy", "Recommended next action", E.STRATEGIC, summary=p.recommended_next_action, next_actions=[p.recommended_next_action])
    child("primary-customer", "market", "Primary customer", E.STRATEGIC, summary=p.target_customer,
          main_assumption="This group can be reached with the founder's current contacts.",
          evidence_gap="Number of reachable customers is UNKNOWN.")
    child("market-context", "market", "Market context", E.UNKNOWN, summary=f"{country or 'Market'}: purchasing power, digital adoption and competition.",
          evidence_gap="Run Phase 1 research to attach sourced context.")
    child("core-problem", "problems", "Core problem", E.STRATEGIC, summary=p.problem, main_assumption=p.problem,
          evidence_gap="No customer interviews recorded yet.", validation_tasks=["Run 5–8 Mom Test interviews with the primary customer."])
    for index, competitor in enumerate(p.competitive_alternatives[:4], start=1):
        child(f"competitor-{index}", "competitors", competitor.name, E.STRATEGIC, summary=competitor.note,
              evidence_gap="Existence and positioning not yet verified by a retrieved source.")
    child("uvp", "value", "Unique value proposition", E.STRATEGIC, summary=p.value_proposition, main_assumption=p.value_proposition)
    for index, risk in enumerate(p.major_risks[:4], start=1):
        child(f"risk-{index}", "risks", f"Risk {index}", E.STRATEGIC, summary=risk, risks=[risk])
    exp = p.first_experiment
    child("first-experiment", "risks", exp.name, E.EXPENSE,
          summary=f"{exp.metric}: target {exp.target:g} within {exp.window_days} days.",
          strategy=exp.method, validation_tasks=[exp.method], main_assumption=exp.threshold_rationale)
    child("core-solution", "product", "Core solution", E.EXPENSE, summary=p.solution)
    child("mvp-scope", "product", "MVP scope", E.EXPENSE, summary="Defined in Phase 3 by the Product Architect agent.",
          evidence_gap="Scope depends on validation results.")
    for index, stream in enumerate(p.revenue_streams[:4], start=1):
        child(f"revenue-stream-{index}", "revenue", stream, E.REVENUE, summary=stream,
              revenue_contribution=MoneyEstimate(amount=None, currency=currency, period="per month", classification=EvidenceClass.UNKNOWN,
                                                 basis="Not estimated until pricing is set in Phase 4."),
              main_assumption="Customers will pay for this.", evidence_gap="Willingness to pay is untested.")
    for index, expense in enumerate(p.main_expenses[:5], start=1):
        child(f"expense-{index}", "costs", expense.item, E.EXPENSE, summary=expense.item, estimated_expense=expense.estimate,
              main_assumption=expense.estimate.basis or "Cost estimate is an assumption.")
    child("channels", "marketing", "Acquisition channels", E.MIXED, summary="To be chosen from validation results.",
          evidence_gap="No channel has been tested.")
    child("launch-sequence", "launch", "Launch sequence", E.MIXED, summary="Store page draft, approved announcements, MOCKED checkout and delivery.")
    child("support", "operations", "Support and delivery", E.EXPENSE, summary="Support workflow and delivery of access to buyers.")
    child("metrics", "operations", "Metrics", E.STRATEGIC, summary="Experiment results, conversion, refunds, support load.")

    return {
        "title": p.business_name,
        "one_liner": p.one_liner,
        "product_category": p.product_category,
        "target_customer": p.target_customer,
        "currency": currency,
        "country": country,
        "nodes": nodes,
    }
