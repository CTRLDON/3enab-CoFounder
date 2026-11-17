import type {
  AgentRun, Artifact, ArtifactSummary, AuditEvent, ChatMessage, DemoScenarios, EvidenceRecord, Founder, FounderProfile,
  Gate, MockOrder, Negotiation, NodeDetail, Opportunity, PhaseView, Plan, Proposal, Reconciliation, SystemStatus, Theme, Venture,
} from "../types/api";
import { getToken } from "./session";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public detail?: unknown) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("X-Founder-Token", token);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(path, { ...init, headers });
  } catch {
    throw new ApiError(0, "network", "Mate's server could not be reached. Check that the backend is running.");
  }
  if (!response.ok) {
    let body: { error?: string; message?: string; detail?: unknown } = {};
    try {
      body = await response.json();
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(response.status, body.error ?? "http_error", body.message ?? `Request failed (${response.status}).`, body.detail);
  }
  const type = response.headers.get("Content-Type") ?? "";
  return (type.includes("application/json") ? response.json() : response.blob()) as Promise<T>;
}

const post = <T>(path: string, body?: unknown) => request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const v = (id: string) => `/api/ventures/${id}`;

export const api = {
  status: (checkModel = true) => request<SystemStatus>(`/api/system/status?check_model=${checkModel}`),
  demoScenarios: () => request<DemoScenarios>("/api/demo/scenarios"),

  createFounder: (display_name: string, profile: FounderProfile) =>
    post<Founder & { founder_token: string }>("/api/founders", { display_name, profile }),
  me: () => request<Founder>("/api/founders/me"),
  updateProfile: (profile: FounderProfile) => request<Founder>("/api/founders/me/profile", { method: "PUT", body: JSON.stringify(profile) }),

  ventures: () => request<{ id: string; title: string; state: string; mode: string; created_at: string }[]>("/api/ventures"),
  createVenture: (mode: "live" | "demo", demo_scenario?: string) => post<Venture>("/api/ventures", { mode, demo_scenario }),
  venture: (id: string) => request<Venture>(v(id)),
  discovery: (id: string) => post<{ venture: Venture }>(`${v(id)}/discovery`),
  stop: (id: string, reason: string) => post<Venture>(`${v(id)}/stop`, { reason }),
  reopen: (id: string, reason: string) => post<Venture>(`${v(id)}/reopen`, { reason }),
  theme: (id: string) => request<Theme>(`${v(id)}/theme`),
  exportVenture: (id: string) => request<Record<string, unknown>>(`${v(id)}/export`),

  conversation: (id: string) => request<{ messages: ChatMessage[] }>(`${v(id)}/conversation`),
  debate: (id: string, message: string) => post<{ founder_message: ChatMessage; reply: ChatMessage; venture: Venture }>(`${v(id)}/debate`, { message }),
  compare: (id: string) => post<{ artifact_id: string; summary: string; opportunities: Opportunity[] }>(`${v(id)}/opportunities`),
  requestProposal: (id: string) => post<{ proposal: Proposal; venture: Venture }>(`${v(id)}/proposals`),
  decideProposal: (id: string, proposalId: string, decision: "approve" | "reject", reason: string) =>
    post<{ venture: Venture; plan: Plan | null }>(`${v(id)}/proposals/${proposalId}/decision`, { decision, reason }),

  plan: (id: string) => request<Plan>(`${v(id)}/plan`),
  node: (id: string, nodeId: string) => request<NodeDetail>(`${v(id)}/plan/nodes/${nodeId}`),
  openNegotiation: (id: string, node_id: string, message: string) => post<Negotiation>(`${v(id)}/negotiations`, { node_id, message }),
  negotiation: (id: string, sid: string) => request<Negotiation>(`${v(id)}/negotiations/${sid}`),
  negotiate: (id: string, sid: string, message: string) => post<Negotiation>(`${v(id)}/negotiations/${sid}/messages`, { message }),
  decideNegotiation: (id: string, sid: string, decision: "approve" | "reject", expected_version: number) =>
    post<{ plan: Plan; negotiation: Negotiation }>(`${v(id)}/negotiations/${sid}/decision`, { decision, expected_version, reason: "" }),

  phases: (id: string) => request<PhaseView[]>(`${v(id)}/phases`),
  runPhase: (id: string, phase: number) => post<{ phases: PhaseView[]; venture: Venture }>(`${v(id)}/phases/${phase}/run`),
  gate: (id: string, phase: number) => post<{ gate: Gate; venture: Venture }>(`${v(id)}/phases/${phase}/gate`),
  recordResult: (id: string, experimentId: string, observed: number, source: string, note: string) =>
    post(`${v(id)}/experiments/${experimentId}/results`, { observed, source, note }),
  approve: (id: string, subject_type: string, decision: "approve" | "reject", reason = "") =>
    post(`${v(id)}/approvals`, { subject_type, decision, reason }),
  evidence: (id: string) => request<EvidenceRecord[]>(`${v(id)}/evidence`),

  artifacts: (id: string) => request<ArtifactSummary[]>(`${v(id)}/artifacts`),
  artifact: (id: string, artifactId: string) => request<Artifact>(`${v(id)}/artifacts/${artifactId}`),
  exportBundle: (id: string, artifactId: string) => request<Blob>(`${v(id)}/artifacts/${artifactId}/export`),

  commerce: (id: string) => request<{ orders: MockOrder[]; reconciliation: Reconciliation }>(`${v(id)}/mock-commerce`),
  mockPurchase: (id: string) => post<MockOrder>(`${v(id)}/mock-commerce/orders`),
  mockDeliver: (id: string, orderId: string, event_id: string) =>
    post<{ duplicate_event: boolean }>(`${v(id)}/mock-commerce/orders/${orderId}/deliver`, { event_id }),
  mockRefund: (id: string, orderId: string, event_id: string) => post(`${v(id)}/mock-commerce/orders/${orderId}/refund`, { event_id }),
  tickets: (id: string) => request<{ id: string; subject: string; body: string; source: string; category: string | null; draft_reply: string | null; status: string; labels: string[] }[]>(`${v(id)}/support-tickets`),
  createTicket: (id: string, subject: string, body: string, source: string) => post(`${v(id)}/support-tickets`, { subject, body, source }),

  audit: (id: string) => request<{ events: AuditEvent[]; agent_runs: AgentRun[]; cost_note: string }>(`${v(id)}/audit`),
};
