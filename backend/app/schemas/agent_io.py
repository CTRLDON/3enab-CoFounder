"""Typed output contracts for every agent.

Each model is sent to the model provider (Gemini or Ollama) as a JSON schema (structured output) and validated again here.
None of these schemas lets a model set a gate outcome, an approval or an evidence 'VERIFIED' flag:
those are decided by deterministic backend code.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import EconomicClass, EvidenceClass, MoneyEstimate

# --- Founder Discovery Agent ------------------------------------------------------------------


class FounderInsights(BaseModel):
    summary: str = Field(max_length=800)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)
    constraints: list[str] = Field(default_factory=list, max_length=8)
    advantage_areas: list[str] = Field(default_factory=list, max_length=6)
    open_questions: list[str] = Field(default_factory=list, max_length=5)


# --- Skeptical Co-Founder Agent: debate --------------------------------------------------------


class AssumptionItem(BaseModel):
    statement: str = Field(max_length=300)
    classification: EvidenceClass = EvidenceClass.ASSUMPTION
    why_it_matters: str = Field(default="", max_length=300)


class AlternativeIdea(BaseModel):
    title: str = Field(max_length=120)
    one_liner: str = Field(max_length=300)
    why_better_fit: str = Field(default="", max_length=300)


class Readiness(BaseModel):
    problem_defined: bool = False
    customer_defined: bool = False
    founder_fit_assessed: bool = False
    differentiation_identified: bool = False
    feasible_with_resources: bool = False
    first_experiment_identified: bool = False
    missing: list[str] = Field(default_factory=list, max_length=6)


DebateStance = Literal["CHALLENGE", "PROBE", "AGREE_WITH_CAVEATS", "RECOMMEND_PIVOT", "RECOMMEND_STOP"]


class DebateTurn(BaseModel):
    message: str = Field(max_length=2500)
    stance: DebateStance
    key_question: str | None = Field(default=None, max_length=400)
    assumptions: list[AssumptionItem] = Field(default_factory=list, max_length=6)
    concerns: list[str] = Field(default_factory=list, max_length=6)
    alternatives: list[AlternativeIdea] = Field(default_factory=list, max_length=3)
    readiness: Readiness = Field(default_factory=Readiness)
    recommend_proposal: bool = False
    working_title: str | None = Field(default=None, max_length=120)


# --- Opportunity Evaluation Agent ---------------------------------------------------------------

Criterion = Literal[
    "founder_fit",
    "problem_severity",
    "demand_evidence",
    "differentiation",
    "capital_requirements",
    "technical_complexity",
    "time_to_mvp",
    "customer_reach",
    "operational_complexity",
    "regulatory_constraints",
    "risk",
    "commercial_viability",
]


class CriterionScore(BaseModel):
    criterion: Criterion
    score: int = Field(ge=1, le=5, description="5 = most favourable for this founder")
    rationale: str = Field(max_length=300)
    evidence: EvidenceClass = EvidenceClass.ASSUMPTION


class Opportunity(BaseModel):
    key: str = Field(max_length=40)
    title: str = Field(max_length=120)
    description: str = Field(max_length=500)
    target_customer: str = Field(max_length=300)
    estimated_startup_cost: MoneyEstimate = Field(default_factory=MoneyEstimate)
    scores: list[CriterionScore] = Field(min_length=1, max_length=12)
    main_uncertainty: str = Field(max_length=300)
    next_experiment: str = Field(max_length=300)


class OpportunityComparison(BaseModel):
    opportunities: list[Opportunity] = Field(min_length=2, max_length=3)
    summary: str = Field(max_length=800)


# --- Business proposal ---------------------------------------------------------------------------


class ExpenseItem(BaseModel):
    item: str = Field(max_length=160)
    estimate: MoneyEstimate = Field(default_factory=MoneyEstimate)


class CompetitorMention(BaseModel):
    name: str = Field(max_length=120)
    note: str = Field(default="", max_length=300)


class ExperimentDraft(BaseModel):
    name: str = Field(max_length=160)
    method: str = Field(max_length=500)
    metric: str = Field(max_length=120)
    target: float = Field(gt=0)
    window_days: int = Field(ge=1, le=120)
    threshold_rationale: str = Field(default="", max_length=400)


ProposalRecommendation = Literal["PROCEED_TO_VALIDATION", "VALIDATE_CAREFULLY", "DO_NOT_PROCEED"]


class ProposalDraft(BaseModel):
    business_name: str = Field(max_length=120)
    one_liner: str = Field(max_length=300)
    product_category: str = Field(max_length=120)
    problem: str = Field(max_length=800)
    target_customer: str = Field(max_length=500)
    solution: str = Field(max_length=800)
    founder_fit: str = Field(max_length=600)
    founder_fit_score: int = Field(ge=1, le=5)
    value_proposition: str = Field(max_length=500)
    business_model: str = Field(max_length=500)
    revenue_streams: list[str] = Field(max_length=6)
    main_expenses: list[ExpenseItem] = Field(default_factory=list, max_length=8)
    estimated_startup_capital: MoneyEstimate = Field(default_factory=MoneyEstimate)
    competitive_alternatives: list[CompetitorMention] = Field(default_factory=list, max_length=6)
    major_risks: list[str] = Field(max_length=8)
    missing_evidence: list[str] = Field(max_length=8)
    first_experiment: ExperimentDraft
    reasons_for: list[str] = Field(max_length=6)
    reasons_against: list[str] = Field(max_length=6)
    recommendation: ProposalRecommendation
    recommended_next_action: str = Field(max_length=400)


# --- Node edit negotiation -----------------------------------------------------------------------

EditableField = Literal[
    "title",
    "summary",
    "objective",
    "explanation",
    "strategy",
    "main_assumption",
    "evidence_gap",
    "economic_class",
    "requirements",
    "risks",
    "assumptions",
    "validation_tasks",
    "next_actions",
]


class NodeFieldChange(BaseModel):
    node_id: str = Field(max_length=64)
    field: EditableField
    value: str | list[str]


class ProposedRevision(BaseModel):
    current_plan: str = Field(max_length=800)
    proposed_plan: str = Field(max_length=800)
    reasons: list[str] = Field(max_length=6)
    consequences: list[str] = Field(max_length=6)
    affected_nodes: list[str] = Field(max_length=12)
    remaining_risks: list[str] = Field(max_length=6)
    changes: list[NodeFieldChange] = Field(min_length=1, max_length=12)


class NegotiationTurn(BaseModel):
    message: str = Field(max_length=2000)
    position: Literal["AGREE", "DISAGREE", "COUNTER_PROPOSAL", "NEED_INFO"]
    ready_to_propose: bool = False
    revision: ProposedRevision | None = None


# --- Market Research Agent -----------------------------------------------------------------------

IndicatorHint = Literal["internet_users", "gdp_per_capita", "inflation", "population", "none"]


class ResearchQuestion(BaseModel):
    question: str = Field(max_length=300)
    why_it_matters: str = Field(max_length=300)
    related_node_id: str | None = Field(default=None, max_length=64)
    indicator_hint: IndicatorHint = "none"


class ResearchPlan(BaseModel):
    questions: list[ResearchQuestion] = Field(min_length=1, max_length=6)
    competitor_candidates: list[str] = Field(default_factory=list, max_length=6)
    customer_problem_hypotheses: list[str] = Field(default_factory=list, max_length=5)


# --- Validation Agent ------------------------------------------------------------------------------


class LeanCanvas(BaseModel):
    problem: list[str] = Field(max_length=3)
    customer_segments: list[str] = Field(max_length=3)
    unique_value_proposition: str = Field(max_length=300)
    solution: list[str] = Field(max_length=3)
    channels: list[str] = Field(max_length=4)
    revenue_streams: list[str] = Field(max_length=3)
    cost_structure: list[str] = Field(max_length=4)
    key_metrics: list[str] = Field(max_length=4)
    unfair_advantage: str = Field(max_length=300)


class RiskyAssumption(BaseModel):
    statement: str = Field(max_length=300)
    risk: Literal["high", "medium", "low"]
    node_id: str | None = Field(default=None, max_length=64)
    how_to_test: str = Field(max_length=300)


class LandingPageCopy(BaseModel):
    headline: str = Field(max_length=120)
    subheadline: str = Field(max_length=240)
    benefits: list[str] = Field(max_length=4)
    call_to_action: str = Field(max_length=40)
    waitlist_question: str = Field(max_length=160)


class InterviewPlan(BaseModel):
    target_profile: str = Field(max_length=300)
    recruiting_channels: list[str] = Field(max_length=5)
    questions: list[str] = Field(min_length=3, max_length=10)
    avoid: list[str] = Field(default_factory=list, max_length=5)


class ValidationPack(BaseModel):
    lean_canvas: LeanCanvas
    riskiest_assumptions: list[RiskyAssumption] = Field(min_length=1, max_length=5)
    landing_page: LandingPageCopy
    extra_experiments: list[ExperimentDraft] = Field(default_factory=list, max_length=2)


# --- Product Architect + MVP Builder --------------------------------------------------------------

Capability = Literal[
    "create_records",
    "edit_records",
    "delete_records",
    "search",
    "filter_by_status",
    "status_workflow",
    "due_dates",
    "summary_stats",
    "csv_export",
    "json_export",
    "local_persistence",
]


class FieldSpec(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,30}$")
    label: str = Field(max_length=60)
    type: Literal["text", "longtext", "number", "date", "select"]
    options: list[str] = Field(default_factory=list, max_length=12)
    required: bool = False

    @field_validator("key")
    @classmethod
    def _not_reserved(cls, value: str) -> str:
        if value in {"id", "status"}:
            raise ValueError("'id' and 'status' are reserved field keys")
        return value

    @model_validator(mode="after")
    def _select_has_options(self) -> "FieldSpec":
        if self.type == "select" and not self.options:
            raise ValueError("select fields need at least one option")
        return self


class EntitySpec(BaseModel):
    name_singular: str = Field(max_length=40)
    name_plural: str = Field(max_length=40)
    fields: list[FieldSpec] = Field(min_length=1, max_length=10)
    status_options: list[str] = Field(min_length=2, max_length=6)


class FeatureSpec(BaseModel):
    name: str = Field(max_length=120)
    capability: Capability
    user_value: str = Field(max_length=300)


class UserJourney(BaseModel):
    name: str = Field(max_length=120)
    steps: list[str] = Field(min_length=1, max_length=8)


class ProductSpec(BaseModel):
    product_name: str = Field(max_length=80)
    problem_statement: str = Field(max_length=500)
    primary_user: str = Field(max_length=300)
    user_journeys: list[UserJourney] = Field(min_length=1, max_length=4)
    must_have_features: list[FeatureSpec] = Field(min_length=3, max_length=11)
    out_of_scope: list[str] = Field(default_factory=list, max_length=8)
    entity: EntitySpec
    acceptance_criteria: list[str] = Field(min_length=2, max_length=8)
    tech_choices: list[str] = Field(default_factory=list, max_length=6)


class MvpCopy(BaseModel):
    app_title: str = Field(max_length=60)
    tagline: str = Field(max_length=160)
    empty_state: str = Field(max_length=200)
    getting_started: list[str] = Field(min_length=2, max_length=6)
    privacy_note: str = Field(max_length=300)


# --- Commercial Agent ------------------------------------------------------------------------------


class PriceTier(BaseModel):
    name: str = Field(max_length=60)
    price: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    period: Literal["one_time", "monthly", "quarterly", "per_term_4_months", "yearly"]
    includes: list[str] = Field(max_length=6)


class CostAssumption(BaseModel):
    item: str = Field(max_length=160)
    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    kind: Literal["fixed_monthly", "one_time", "variable_per_sale"]
    classification: EvidenceClass = EvidenceClass.ASSUMPTION
    basis: str = Field(default="", max_length=300)


class PolicySpecifics(BaseModel):
    refund_window_days: int = Field(ge=0, le=90)
    data_collected: list[str] = Field(max_length=8)
    governing_region: str = Field(max_length=80)
    support_channel: str = Field(max_length=120)


class ChecklistItem(BaseModel):
    item: str = Field(max_length=200)
    why: str = Field(max_length=300)


class CommercialPack(BaseModel):
    pricing_model: str = Field(max_length=300)
    tiers: list[PriceTier] = Field(min_length=1, max_length=3)
    price_rationale: str = Field(max_length=800)
    cost_assumptions: list[CostAssumption] = Field(min_length=1, max_length=10)
    policy_specifics: PolicySpecifics
    compliance_checklist: list[ChecklistItem] = Field(min_length=2, max_length=10)
    operational_requirements: list[str] = Field(default_factory=list, max_length=8)


# --- Launch Agent ----------------------------------------------------------------------------------


class Announcement(BaseModel):
    channel: str = Field(max_length=60)
    text: str = Field(max_length=800)


class LaunchChecklistItem(BaseModel):
    item: str = Field(max_length=200)
    owner: Literal["founder", "system"]


class LaunchPack(BaseModel):
    store_headline: str = Field(max_length=120)
    product_description: str = Field(max_length=1200)
    feature_bullets: list[str] = Field(min_length=2, max_length=6)
    announcements: list[Announcement] = Field(min_length=1, max_length=4)
    launch_checklist: list[LaunchChecklistItem] = Field(min_length=3, max_length=12)
    delivery_message: str = Field(max_length=800)


# --- Operations Agent ------------------------------------------------------------------------------


class PersevereMemo(BaseModel):
    recommendation: Literal["CONTINUE", "REPEAT_EXPERIMENT", "PIVOT", "STOP"]
    summary: str = Field(max_length=1200)
    what_we_learned: list[str] = Field(max_length=6)
    evidence_gaps: list[str] = Field(max_length=6)
    next_experiments: list[str] = Field(max_length=4)


class OperationsReview(BaseModel):
    support_workflow: list[str] = Field(min_length=2, max_length=8)
    support_categories: list[str] = Field(min_length=2, max_length=6)
    memo: PersevereMemo


class TicketTriage(BaseModel):
    category: str = Field(max_length=60)
    priority: Literal["low", "normal", "high"]
    draft_reply: str = Field(max_length=1200)
    needs_founder: bool = True


# --- Gatekeeper Agent --------------------------------------------------------------------------------


class GateCommentary(BaseModel):
    """The model may explain a gate result. It cannot change it: there is no outcome field."""

    commentary: str = Field(max_length=1200)
    suggested_next_steps: list[str] = Field(default_factory=list, max_length=4)


# --- Plan nodes (used by the plan builder and the negotiation diff) ----------------------------------


class PlanNodeModel(BaseModel):
    id: str
    parent_id: str | None = None
    title: str
    category: str
    economic_class: EconomicClass = EconomicClass.UNKNOWN
    summary: str = ""
    objective: str = ""
    explanation: str = ""
    strategy: str = ""
    main_assumption: str = ""
    evidence_gap: str = ""
    requirements: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    validation_tasks: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    estimated_expense: MoneyEstimate | None = None
    revenue_contribution: MoneyEstimate | None = None
    phase: int = 1
