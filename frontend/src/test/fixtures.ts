import type { Plan, PlanNode, Venture } from "../types/api";

const node = (id: string, parent: string | null, title: string, economic_class: PlanNode["economic_class"] = "strategic"): PlanNode => ({
  id, parent_id: parent, title, category: parent ?? "venture", economic_class, summary: `${title} summary`, objective: `${title} objective`,
  explanation: "", strategy: "", main_assumption: "Main assumption text", evidence_gap: "Gap text", requirements: [], dependencies: [],
  risks: [], assumptions: [], validation_tasks: [], next_actions: [], estimated_expense: null, revenue_contribution: null, phase: 1,
});

export const PLAN: Plan = {
  plan_id: "p1", version: 1, current_version: 1, reason: "Created", created_by: "founder", created_at: "2026-11-17T10:00:00Z",
  document: {
    title: "Test venture", one_liner: "A test", product_category: "tool", target_customer: "teams", currency: "EGP", country: "Egypt",
    nodes: [
      node("venture", null, "Test venture"),
      node("strategy", "venture", "Business strategy"),
      node("market", "venture", "Target market"),
      node("revenue", "venture", "Revenue model", "revenue"),
      node("costs", "venture", "Costs and resources", "expense"),
      node("revenue-stream-1", "revenue", "Monthly subscription", "revenue"),
      node("expense-1", "costs", "Hosting", "expense"),
    ],
  },
  node_status: {
    venture: { progress: "active", evidence: {}, revisions: 0 },
    revenue: { progress: "upcoming", evidence: { ASSUMPTION: 2 }, revisions: 0 },
  },
  versions: [{ version: 1, reason: "Created", created_by: "founder", created_at: "2026-11-17T10:00:00Z" }],
  open_negotiations: [],
};

export const VENTURE: Venture = {
  id: "v1", title: "Test venture", state: "WORKSPACE_ACTIVE", mode: "demo", demo_scenario: "main", labels: ["SCRIPTED DEMO"],
  current_phase: 1, founder_insights: null, proposals: [], plan_version: 1, gates: {}, transitions: [], created_at: "2026-11-17T10:00:00Z",
};
