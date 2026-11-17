// Types mirroring the backend read models (backend/app/api/views.py and schemas/).

export type EvidenceClass = "VERIFIED" | "ESTIMATE" | "ASSUMPTION" | "PROJECTION" | "MOCKED" | "UNKNOWN";
export type EconomicClass = "revenue" | "expense" | "mixed" | "strategic" | "unknown";
export type GateOutcome = "GO" | "REPEAT" | "PIVOT" | "STOP";
export type VentureState =
  | "ONBOARDING" | "DISCOVERY" | "DEBATE" | "PROPOSAL_READY" | "AWAITING_FOUNDER_APPROVAL" | "PLAN_APPROVED"
  | "WORKSPACE_ACTIVE" | "VALIDATING" | "BUILDING" | "COMMERCIAL_REVIEW" | "LAUNCH_SIMULATION" | "OPERATING"
  | "PIVOT_REQUIRED" | "STOPPED";

export interface FounderProfile {
  background: {
    education: string; skills: string[]; experience: string; entrepreneurial_experience: string;
    industries: string[]; interests: string[];
  };
  resources: {
    budget_amount: number | null; budget_currency: string; weekly_hours: number | null; technical_resources: string;
    business_contacts: string; customer_access: string; team: string; existing_assets: string;
  };
  preferences: {
    has_idea: boolean; starting_idea: string; problems_of_interest: string[]; target_country: string;
    preferred_audience: string; business_type: "B2B" | "B2C" | "either"; risk_tolerance: "low" | "medium" | "high";
    short_term_goal: string; long_term_goal: string; values_and_constraints: string;
  };
}

export interface Founder { id: string; display_name: string; profile: FounderProfile; profile_revision: number }

export interface MoneyEstimate { amount: number | null; currency: string; period: string; classification: EvidenceClass; basis: string }

export interface Assumption { statement: string; classification: EvidenceClass; why_it_matters: string }
export interface Readiness {
  problem_defined: boolean; customer_defined: boolean; founder_fit_assessed: boolean;
  differentiation_identified: boolean; feasible_with_resources: boolean; first_experiment_identified: boolean; missing: string[];
}
export interface DebateStructured {
  stance?: string; key_question?: string | null; assumptions?: Assumption[]; concerns?: string[];
  alternatives?: { title: string; one_liner: string; why_better_fit: string }[];
  readiness?: Readiness; recommend_proposal?: boolean; readiness_complete?: boolean;
  policy?: boolean; findings?: { rule: string; message: string }[];
  kind?: string; proposal_id?: string; artifact_id?: string;
  position?: string; ready_to_propose?: boolean; revision?: ProposedRevision | null; revision_rejected_by_validator?: string[];
}
export interface ChatMessage {
  id: number; seq?: number; role: "founder" | "agent" | "system"; agent: string | null; content: string;
  structured: DebateStructured | null; created_at: string;
}

export interface ProposalData {
  business_name: string; one_liner: string; product_category: string; problem: string; target_customer: string;
  solution: string; founder_fit: string; founder_fit_score: number; value_proposition: string; business_model: string;
  revenue_streams: string[]; main_expenses: { item: string; estimate: MoneyEstimate }[];
  estimated_startup_capital: MoneyEstimate; competitive_alternatives: { name: string; note: string }[];
  major_risks: string[]; missing_evidence: string[];
  first_experiment: { name: string; method: string; metric: string; target: number; window_days: number; threshold_rationale: string };
  reasons_for: string[]; reasons_against: string[];
  recommendation: "PROCEED_TO_VALIDATION" | "VALIDATE_CAREFULLY" | "DO_NOT_PROCEED"; recommended_next_action: string;
}
export interface Proposal {
  id: string; number: number; status: "awaiting" | "approved" | "rejected" | "superseded"; data: ProposalData;
  policy_findings: { rule: string; message: string }[]; rejection_reason: string | null; created_at: string; decided_at: string | null;
}

export interface GateCheck { id: string; label: string; passed: boolean; detail: string; severity: string }
export interface Gate {
  id: string; phase: number; outcome: GateOutcome; checks: GateCheck[]; reasoning: string; evidence_basis: string;
  commentary: string | null; created_at: string;
}

export interface Venture {
  id: string; title: string; state: VentureState; mode: "live" | "demo"; demo_scenario: string | null; labels: string[];
  current_phase: number | null; founder_insights: Record<string, unknown> | null; proposals: Proposal[];
  plan_version: number | null; gates: Record<string, Gate>;
  transitions: { from: string; to: string; actor: string; reason: string; at: string }[]; created_at: string;
}

export interface PlanNode {
  id: string; parent_id: string | null; title: string; category: string; economic_class: EconomicClass;
  summary: string; objective: string; explanation: string; strategy: string; main_assumption: string; evidence_gap: string;
  requirements: string[]; dependencies: string[]; risks: string[]; assumptions: string[]; validation_tasks: string[];
  next_actions: string[]; estimated_expense: MoneyEstimate | null; revenue_contribution: MoneyEstimate | null; phase: number;
}
export interface NodeStatus { progress: "active" | "complete" | "upcoming" | "stopped"; evidence: Partial<Record<EvidenceClass, number>>; revisions: number }
export interface Plan {
  plan_id: string; version: number; current_version: number; reason: string; created_by: string; created_at: string;
  document: { title: string; one_liner: string; product_category: string; target_customer: string; currency: string; country: string; nodes: PlanNode[] };
  node_status: Record<string, NodeStatus>;
  versions: { version: number; reason: string; created_by: string; created_at: string }[];
  open_negotiations: { id: string; node_id: string; status: string }[];
}

export interface EvidenceRecord {
  id: string; claim: string; classification: EvidenceClass; source_url: string | null; source_title: string | null;
  published_at: string | null; retrieved_at: string | null; confidence: string; limitations: string; implication?: string;
  research_question?: string | null; node_id: string | null; verification_status: string; created_by?: string;
}
export interface NodeDetail {
  node: PlanNode; evidence: EvidenceRecord[];
  history: { from_version: number; to_version: number; summary: string; approved_by: string; at: string }[];
}

export interface NodeChange { node_id: string; field: string; value: string | string[] }
export interface ProposedRevision {
  current_plan: string; proposed_plan: string; reasons: string[]; consequences: string[]; affected_nodes: string[];
  remaining_risks: string[]; changes: NodeChange[];
}
export interface Negotiation {
  id: string; node_id: string; base_version: number; status: "open" | "proposed" | "approved" | "rejected" | "conflict";
  proposed_change: ProposedRevision | null; messages: ChatMessage[];
}

export interface ArtifactSummary { id: string; phase: number; kind: string; title: string; content_type: string; labels: string[]; created_at: string }
export interface Artifact extends ArtifactSummary { content: string | Record<string, string>; meta: Record<string, unknown> }

export interface Experiment {
  id: string; name: string; metric: string; target: number; window_days: number; locked_at: string | null;
  results: { observed: number; source: string; note: string; evidence_url: string | null; at: string }[];
}
export interface PhaseView {
  phase: number; name: string; status: "active" | "passed" | "locked" | "stop" | "pivot"; agents: string[];
  artifacts: ArtifactSummary[]; gate: Gate | null; experiments: Experiment[];
}

export interface Theme {
  archetype: string; label: string; rationale: string; matched_terms: string[]; source: string; state_note: string | null;
  tokens: Record<string, string>;
  contrast: { foreground: string; background: string; ratio: number; required: number; passes: boolean }[];
  all_contrast_checks_pass: boolean;
}

export interface Opportunity {
  key: string; title: string; description: string; target_customer: string; estimated_startup_cost: MoneyEstimate;
  scores: { criterion: string; score: number; rationale: string; evidence: EvidenceClass }[];
  main_uncertainty: string; next_experiment: string; heuristic_index: number; budget_check: string;
}

export interface MockOrder {
  id: string; label: "MOCKED"; buyer: string; sku: string; amount: number; currency: string; status: string;
  entitlement: { id: string; access_key: string; status: string; revoked_at: string | null } | null;
}
export interface Reconciliation {
  label: string; note: string; balanced: boolean; mismatches: string[]; totals: Record<string, number>;
  orders: { order_id: string; buyer: string; status: string; charge: number; fee: number; refund: number; mock_payout: number; access: string; currency: string }[];
}

export interface AuditEvent {
  id: number; timestamp: string; agent: string; action: string; sources: string[]; model: string | null; cost: number;
  approved_by: string | null; outcome?: string; execution_mode: string; detail: Record<string, unknown>;
}
export interface AgentRun {
  id: string; agent: string; task: string; status: string; model: string | null; execution_mode: string; error: string | null;
  prompt_tokens: number | null; completion_tokens: number | null; duration_ms: number; attempts: number; created_at: string;
}

export interface SystemStatus {
  default_mode: "live" | "demo";
  model: { provider: "gemini" | "ollama"; model: string; reachable?: boolean; model_installed?: boolean; detail?: string | null; checked: boolean };
  external_actions_enabled: boolean; payments: string; research_online: boolean;
  agents: { name: string; responsibility: string; tools: string[]; prompt: string }[];
}

export interface DemoScenarios {
  label: string; note: string;
  scenarios: Record<string, {
    founder: { display_name: string; profile: FounderProfile };
    script: { debate: string[]; reject_reason: string; negotiation_node: string | null; negotiation: string[];
      experiment_results: { observed: number; note: string }[]; support_ticket: { subject: string; body: string } | null };
  }>;
}

export interface ApiErrorBody { error: string; message: string; detail?: unknown }
