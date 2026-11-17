import type { VentureState } from "../types/api";

export const STATE_LABEL: Record<VentureState, string> = {
  ONBOARDING: "Getting to know you",
  DISCOVERY: "Ready to discuss",
  DEBATE: "In discussion",
  PROPOSAL_READY: "Proposal drafted",
  AWAITING_FOUNDER_APPROVAL: "Waiting for your decision",
  PLAN_APPROVED: "Plan approved",
  WORKSPACE_ACTIVE: "Phase 1: Discover",
  VALIDATING: "Phase 2: Validate",
  BUILDING: "Phase 3: Build",
  COMMERCIAL_REVIEW: "Phase 4: Commercial setup",
  LAUNCH_SIMULATION: "Phase 5: Launch (mocked)",
  OPERATING: "Phase 6: Operate and learn",
  PIVOT_REQUIRED: "Pivot required",
  STOPPED: "Stopped",
};

export const PRE_PLAN_STATES: VentureState[] = ["ONBOARDING", "DISCOVERY", "DEBATE", "PROPOSAL_READY", "AWAITING_FOUNDER_APPROVAL"];

export function hasWorkspace(state: VentureState, planVersion: number | null): boolean {
  return planVersion !== null && !PRE_PLAN_STATES.includes(state);
}
