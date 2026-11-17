"""Opportunity Evaluation Agent + deterministic heuristic scoring.

The model scores each criterion 1-5 with a rationale; this module computes the weighted index in
code with published weights. The index is a heuristic for comparison, not a probability of success.
"""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import OpportunityComparison
from app.schemas.founder import FounderProfileData
from app.services.context import founder_context, transcript

CRITERIA_WEIGHTS: dict[str, float] = {
    "founder_fit": 1.5,
    "problem_severity": 1.5,
    "demand_evidence": 1.25,
    "customer_reach": 1.25,
    "differentiation": 1.0,
    "capital_requirements": 1.0,
    "time_to_mvp": 1.0,
    "commercial_viability": 1.0,
    "technical_complexity": 0.75,
    "regulatory_constraints": 0.75,
    "risk": 0.75,
    "operational_complexity": 0.5,
}
CRITERIA_LABELS: dict[str, str] = {
    "founder_fit": "Founder–idea fit",
    "problem_severity": "Customer problem severity",
    "demand_evidence": "Market demand evidence",
    "customer_reach": "Ability to reach customers",
    "differentiation": "Competitive differentiation",
    "capital_requirements": "Start-up capital required",
    "time_to_mvp": "Time to first testable MVP",
    "commercial_viability": "Potential commercial viability",
    "technical_complexity": "Technical complexity",
    "regulatory_constraints": "Regulatory constraints",
    "risk": "Risk",
    "operational_complexity": "Operational complexity",
}


def score_opportunities(comparison: OpportunityComparison, budget: float | None, currency: str) -> list[dict[str, Any]]:
    scored = []
    for opp in comparison.opportunities:
        by_criterion = {s.criterion: s for s in opp.scores}
        weight_sum = sum(CRITERIA_WEIGHTS[c] for c in by_criterion)
        weighted = sum(CRITERIA_WEIGHTS[c] * s.score for c, s in by_criterion.items())
        index = round((weighted / weight_sum - 1) / 4 * 100) if weight_sum else 0
        cost = opp.estimated_startup_cost
        budget_check = "unknown"
        if budget is not None and cost.amount is not None and cost.currency == currency:
            budget_check = "within_budget" if cost.amount <= budget else ("stretch" if cost.amount <= 3 * budget else "exceeds_budget")
        scored.append(
            {
                **opp.model_dump(mode="json"),
                "heuristic_index": index,
                "missing_criteria": [c for c in CRITERIA_WEIGHTS if c not in by_criterion],
                "budget_check": budget_check,
            }
        )
    return sorted(scored, key=lambda o: o["heuristic_index"], reverse=True)


class OpportunityEvaluationAgent(BaseAgent):
    name = "opportunity_evaluation"
    prompt_file = "opportunity_evaluation.md"
    tools = ("read:founder_profile", "read:conversation")
    responsibility = "Compare candidate directions on transparent criteria."

    def compare(self, ctx: AgentContext, *, profile: FounderProfileData, history: list[dict[str, Any]], turn: int) -> OpportunityComparison:
        criteria = "\n".join(f"- {key}: {label}" for key, label in CRITERIA_LABELS.items())
        content = (
            founder_context(profile)
            + "\n\nCompare two or three realistic directions raised in the discussion (include the founder's own idea "
            "if it is still on the table). Score every criterion from 1 to 5 where 5 is MOST favourable for this "
            f"founder (so low capital needs score high). Criteria:\n{criteria}\n"
            "Mark each score's evidence class honestly; without retrieved sources that is ASSUMPTION."
        )
        return self.call(ctx, task="compare_opportunities", schema=OpportunityComparison, user_content=content,
                         history=transcript(history), script_turn=turn)
