"""Venture orchestrator: sequences agents, persists their outputs and moves the state machine.

Responsibilities are split deliberately:
  * agents produce typed data (agents/)
  * approvals come only from the founder (workflows/approval.py)
  * gates decide outcomes deterministically (workflows/gates.py)
  * this module wires them together and enforces which step may run in which state
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.base import AgentContext
from app.agents.gatekeeper import GatekeeperAgent
from app.agents.founder_discovery import FounderDiscoveryAgent
from app.agents.opportunity_evaluation import OpportunityEvaluationAgent, score_opportunities
from app.agents.skeptical_cofounder import SkepticalCofounderAgent
from app.errors import AgentFailure, InvalidTransition, NotFound, PolicyViolation, VersionConflict
from app.models import (
    BusinessProposal,
    Conversation,
    FounderProfile,
    GateDecision,
    GeneratedArtifact,
    Message,
    NegotiationSession,
    Venture,
    utcnow,
)
from app.schemas.agent_io import NegotiationTurn, ProposalDraft, ProposedRevision
from app.schemas.founder import FounderProfileData
from app.services import plan_versioning, renderers
from app.services.audit_log import AuditLogger
from app.services.gateway_registry import gateway_for
from app.services.plan_builder import build_initial_plan
from app.services.safety import SafetyReport, refusal_message, screen_founder_message, screen_venture_category
from app.services.theme_service import theme_for
from app.workflows import approval as approvals
from app.workflows import gates
from app.workflows.state_machine import PHASE_STATE, VentureState, transition

S = VentureState
PHASE_NAMES = {1: "Discover", 2: "Validate", 3: "Build", 4: "Commercial setup", 5: "Launch (MOCKED commerce)", 6: "Operate and learn"}
WORKSPACE_STATES = {S.WORKSPACE_ACTIVE, S.VALIDATING, S.BUILDING, S.COMMERCIAL_REVIEW, S.LAUNCH_SIMULATION, S.OPERATING}
GATE_TARGET = {1: S.VALIDATING, 2: S.BUILDING, 3: S.COMMERCIAL_REVIEW, 4: S.LAUNCH_SIMULATION, 5: S.OPERATING, 6: S.OPERATING}


def message_view(m: Message) -> dict[str, Any]:
    return {
        "id": m.id, "seq": m.seq, "role": m.role, "agent": m.agent, "content": m.content,
        "structured": m.structured, "created_at": m.created_at.isoformat(),
    }


class Orchestrator:
    def __init__(self, db: Session, venture: Venture, audit: AuditLogger | None = None) -> None:
        self.db = db
        self.venture = venture
        self.audit = audit or AuditLogger()
        self.gateway = gateway_for(venture)
        self.ctx = AgentContext(db, venture, self.gateway, self.audit)

    # --- basics -------------------------------------------------------------------------------

    @property
    def execution_mode(self) -> str:
        return self.gateway.execution_mode

    def profile(self) -> FounderProfileData:
        row = self.db.scalars(select(FounderProfile).where(FounderProfile.founder_id == self.venture.founder_id)).first()
        if row is None:
            raise NotFound("Founder profile missing.")
        return FounderProfileData.model_validate(row.data)

    def move(self, to_state: VentureState, *, actor: str, reason: str) -> None:
        transition(self.db, self.venture, to_state, actor=actor, reason=reason, audit=self.audit, execution_mode="deterministic_rule")

    def require_state(self, allowed: set[VentureState], action: str) -> None:
        if self.venture.state not in allowed:
            raise InvalidTransition(
                f"Cannot {action} while the venture is {self.venture.state}.",
                state=self.venture.state,
                allowed=sorted(s.value for s in allowed),
            )

    def conversation(self, kind: str = "debate") -> Conversation:
        conv = self.db.scalars(
            select(Conversation).where(Conversation.venture_id == self.venture.id, Conversation.kind == kind).order_by(Conversation.created_at)
        ).first()
        if conv is None:
            conv = Conversation(venture_id=self.venture.id, kind=kind)
            self.db.add(conv)
            self.db.flush()
        return conv

    def add_message(self, conv: Conversation, role: str, content: str, *, agent: str | None = None,
                    structured: dict[str, Any] | None = None) -> Message:
        seq = (self.db.scalar(select(func.max(Message.seq)).where(Message.conversation_id == conv.id)) or 0) + 1
        msg = Message(conversation_id=conv.id, seq=seq, role=role, agent=agent, content=content, structured=structured)
        self.db.add(msg)
        self.db.flush()
        return msg

    def history(self, conv: Conversation) -> list[dict[str, Any]]:
        rows = self.db.scalars(select(Message).where(Message.conversation_id == conv.id).order_by(Message.seq))
        return [message_view(m) for m in rows]

    def save_artifact(self, phase: int, kind: str, title: str, content_type: str, content: str,
                      labels: list[str] | None = None, meta: dict[str, Any] | None = None) -> GeneratedArtifact:
        labels = list(labels or [])
        if self.venture.mode == "demo" and "SCRIPTED DEMO" not in labels:
            labels.append("SCRIPTED DEMO")
        artifact = GeneratedArtifact(venture_id=self.venture.id, phase=phase, kind=kind, title=title,
                                     content_type=content_type, content=content, labels=labels, meta=meta or {})
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def _policy_refusal(self, conv: Conversation, report: SafetyReport) -> Message:
        text = refusal_message(report)
        msg = self.add_message(conv, "agent", text, agent="policy_guard", structured={
            "policy": True, "findings": [f.__dict__ for f in report.findings],
            "stance": "RECOMMEND_PIVOT" if "prohibited_category" in report.kinds() else "CHALLENGE",
        })
        self.audit.record(self.db, venture_id=self.venture.id, agent="policy_guard", action="policy_refusal",
                          execution_mode="deterministic_rule", detail={"rules": report.rules()})
        return msg

    # --- discovery and debate -----------------------------------------------------------------------

    def run_founder_discovery(self) -> dict[str, Any]:
        self.require_state({S.ONBOARDING, S.DISCOVERY}, "analyse the founder profile")
        insights = FounderDiscoveryAgent().interpret(self.ctx, self.profile())
        self.venture.founder_insights = insights.model_dump(mode="json")
        if self.venture.state == S.ONBOARDING:
            self.move(S.DISCOVERY, actor="founder_discovery", reason="Founder profile analysed.")
        return self.venture.founder_insights

    def debate(self, text: str) -> dict[str, Any]:
        self.require_state({S.DISCOVERY, S.DEBATE}, "continue the discussion (decide on the open proposal first)")
        conv = self.conversation("debate")
        founder_msg = self.add_message(conv, "founder", text)
        if self.venture.state == S.DISCOVERY:
            self.move(S.DEBATE, actor="founder", reason="Founder started the discussion.")
        report = screen_founder_message(text)
        if report.blocked:
            reply = self._policy_refusal(conv, report)
            return {"founder_message": message_view(founder_msg), "reply": message_view(reply)}

        history = [m for m in self.history(conv) if m["id"] != founder_msg.id]
        turn = sum(1 for m in history if m["agent"] == SkepticalCofounderAgent.name)
        result = SkepticalCofounderAgent().debate_turn(
            self.ctx, profile=self.profile(), insights=self.venture.founder_insights, history=history,
            founder_message=text, turn=turn,
        )
        structured = result.model_dump(mode="json")
        checklist = result.readiness.model_dump(exclude={"missing"})
        structured["readiness_complete"] = all(checklist.values())
        reply = self.add_message(conv, "agent", result.message, agent=SkepticalCofounderAgent.name, structured=structured)
        if result.working_title and self.venture.title.startswith("Untitled"):
            self.venture.title = result.working_title
        return {"founder_message": message_view(founder_msg), "reply": message_view(reply)}

    def compare_opportunities(self) -> dict[str, Any]:
        self.require_state({S.DEBATE}, "compare opportunities")
        conv = self.conversation("debate")
        turn = self.db.scalar(select(func.count()).select_from(GeneratedArtifact).where(
            GeneratedArtifact.venture_id == self.venture.id, GeneratedArtifact.kind == "opportunity_comparison")) or 0
        profile = self.profile()
        comparison = OpportunityEvaluationAgent().compare(self.ctx, profile=profile, history=self.history(conv), turn=turn)
        scored = score_opportunities(comparison, profile.resources.budget_amount, profile.resources.budget_currency)
        artifact = self.save_artifact(1, "opportunity_comparison", "Opportunity comparison", "markdown",
                                      renderers.comparison_md(scored, comparison.summary), ["HEURISTIC"],
                                      {"opportunities": scored, "summary": comparison.summary})
        self.add_message(conv, "system", f"Mate compared {len(scored)} directions. See the comparison panel.",
                         structured={"artifact_id": artifact.id, "kind": "opportunity_comparison"})
        return {"artifact_id": artifact.id, "summary": comparison.summary, "opportunities": scored}

    def request_proposal(self) -> BusinessProposal:
        self.require_state({S.DEBATE}, "draft a proposal")
        conv = self.conversation("debate")
        previous = list(self.db.scalars(select(BusinessProposal).where(BusinessProposal.venture_id == self.venture.id)
                                        .order_by(BusinessProposal.number)))
        rejected = [{"number": p.number, "business_name": p.data["business_name"], "reason": p.data.get("_rejection_reason", "")}
                    for p in previous if p.status == "rejected"]
        number = len(previous) + 1
        draft: ProposalDraft = SkepticalCofounderAgent().draft_proposal(
            self.ctx, profile=self.profile(), insights=self.venture.founder_insights,
            history=self.history(conv), rejected=rejected, number=number,
        )
        data = draft.model_dump(mode="json")
        category = screen_venture_category(" ".join([draft.one_liner, draft.product_category, draft.solution]))
        data["_policy_findings"] = [f.__dict__ for f in category.findings]
        proposal = BusinessProposal(venture_id=self.venture.id, number=number, data=data, status="awaiting")
        self.db.add(proposal)
        self.db.flush()
        self.venture.title = draft.business_name
        self.move(S.PROPOSAL_READY, actor=SkepticalCofounderAgent.name, reason=f"Proposal #{number} drafted.")
        self.move(S.AWAITING_FOUNDER_APPROVAL, actor="workflow", reason="Waiting for the founder's decision.")
        self.add_message(conv, "system", f"Mate drafted proposal #{number}: {draft.business_name}. Approve it or keep challenging.",
                         structured={"proposal_id": proposal.id, "kind": "proposal"})
        return proposal

    def decide_proposal(self, proposal_id: str, decision: str, reason: str) -> dict[str, Any]:
        proposal = self.db.get(BusinessProposal, proposal_id)
        if proposal is None or proposal.venture_id != self.venture.id:
            raise NotFound("Proposal not found.")
        if proposal.status != "awaiting" or self.venture.state != S.AWAITING_FOUNDER_APPROVAL:
            raise InvalidTransition(f"Proposal #{proposal.number} is {proposal.status}; it cannot be decided now.")
        conv = self.conversation("debate")
        data = proposal.data

        if decision == "approve":
            category = screen_venture_category(" ".join([data["one_liner"], data["product_category"], data["solution"], data["business_name"]]))
            if category.blocked:  # hard policy: founder approval cannot override
                self.audit.record(self.db, venture_id=self.venture.id, agent="policy_guard", action="block_prohibited_proposal",
                                  execution_mode="deterministic_rule", detail={"rules": category.rules()})
                self.db.commit()
                raise PolicyViolation(refusal_message(category), rules=category.rules())
            approval = approvals.record_decision(self.db, self.venture, subject_type="proposal", subject_id=proposal.id,
                                                 decision="approve", actor="founder", reason=reason, audit=self.audit)
            proposal.status, proposal.decided_at = "approved", utcnow()
            for other in self.db.scalars(select(BusinessProposal).where(BusinessProposal.venture_id == self.venture.id,
                                                                        BusinessProposal.status == "awaiting",
                                                                        BusinessProposal.id != proposal.id)):
                other.status = "superseded"
            profile = self.profile()
            document = build_initial_plan(ProposalDraft.model_validate({k: v for k, v in data.items() if not k.startswith("_")}),
                                          country=profile.preferences.target_country, currency=profile.resources.budget_currency)
            plan, version = plan_versioning.create_plan_from_proposal(self.db, venture_id=self.venture.id, proposal=proposal,
                                                                       approval=approval, document=document)
            self.audit.record(self.db, venture_id=self.venture.id, agent="workflow", action=f"create_plan_v{version.version}",
                              execution_mode="deterministic_rule", approved_by="founder", detail={"proposal": proposal.number})
            self.move(S.PLAN_APPROVED, actor="founder", reason=f"Founder approved proposal #{proposal.number}.")
            self.move(S.WORKSPACE_ACTIVE, actor="workflow", reason="Business workspace created.")
            self.add_message(conv, "system", f"You approved proposal #{proposal.number}. The business workspace is ready.",
                             structured={"proposal_id": proposal.id, "kind": "approved"})
            self.save_artifact(1, "business_proposal", f"Business proposal #{proposal.number}", "markdown",
                               renderers.proposal_md(data, proposal.number, "approved by founder"), ["FOUNDER APPROVED"])
            return {"decision": "approve", "plan_version": version.version, "state": self.venture.state}

        approvals.record_decision(self.db, self.venture, subject_type="proposal", subject_id=proposal.id,
                                  decision="reject", actor="founder", reason=reason, audit=self.audit)
        proposal.status, proposal.decided_at = "rejected", utcnow()
        proposal.data = {**data, "_rejection_reason": reason}
        self.move(S.DEBATE, actor="founder", reason=f"Founder rejected proposal #{proposal.number}.")
        self.add_message(conv, "system", f"You rejected proposal #{proposal.number}" + (f": {reason}" if reason else ".")
                         + " The discussion continues with everything said so far.",
                         structured={"proposal_id": proposal.id, "kind": "rejected"})
        return {"decision": "reject", "state": self.venture.state}

    def stop(self, reason: str) -> None:
        if self.venture.state == S.STOPPED:
            return
        self.move(S.STOPPED, actor="founder", reason=reason or "Founder chose to stop.")

    def reopen(self, reason: str) -> None:
        self.require_state({S.STOPPED, S.PIVOT_REQUIRED}, "reopen the discussion")
        self.move(S.DEBATE, actor="founder", reason=reason or "Founder reopened the discussion.")
        self.add_message(self.conversation("debate"), "system",
                         "Discussion reopened. Earlier gate results and evidence stay on record unchanged.")

    # --- plan editing through negotiation ----------------------------------------------------------------

    def _plan_or_404(self):  # type: ignore[no-untyped-def]
        plan = plan_versioning.get_plan(self.db, self.venture.id)
        if plan is None:
            raise NotFound("No approved plan yet.")
        return plan

    def open_negotiation(self, node_id: str, text: str) -> tuple[NegotiationSession, dict[str, Any]]:
        self.require_state(WORKSPACE_STATES, "edit the plan")
        plan = self._plan_or_404()
        document = plan_versioning.get_version(self.db, plan).data
        if node_id not in {n["id"] for n in document["nodes"]}:
            raise NotFound(f"Node '{node_id}' is not in the plan.")
        conv = Conversation(venture_id=self.venture.id, kind="negotiation")
        self.db.add(conv)
        self.db.flush()
        session = NegotiationSession(venture_id=self.venture.id, node_id=node_id, base_version=plan.current_version,
                                     status="open", conversation_id=conv.id)
        self.db.add(session)
        self.db.flush()
        return session, self.negotiation_message(session, text)

    def negotiation_message(self, session: NegotiationSession, text: str) -> dict[str, Any]:
        if session.status not in {"open", "proposed"}:
            raise InvalidTransition(f"This negotiation is {session.status}.")
        conv = self.db.get(Conversation, session.conversation_id)
        assert conv is not None
        founder_msg = self.add_message(conv, "founder", text)
        report = screen_founder_message(text)
        if report.blocked:
            reply = self._policy_refusal(conv, report)
            return {"founder_message": message_view(founder_msg), "reply": message_view(reply), "status": session.status}
        plan = self._plan_or_404()
        document = plan_versioning.get_version(self.db, plan, session.base_version).data
        history = [m for m in self.history(conv) if m["id"] != founder_msg.id]
        turn = sum(1 for m in history if m["agent"] == SkepticalCofounderAgent.name)
        result: NegotiationTurn = SkepticalCofounderAgent().negotiate(
            self.ctx, plan_document=document, node_id=session.node_id, history=history, founder_message=text, turn=turn)
        structured = result.model_dump(mode="json")
        if result.ready_to_propose and result.revision:
            problems = plan_versioning.validate_changes(document, result.revision.changes)
            if problems:
                structured["revision_rejected_by_validator"] = problems
                session.status, session.proposed_change = "open", None
            else:
                session.status, session.proposed_change = "proposed", result.revision.model_dump(mode="json")
        reply = self.add_message(conv, "agent", result.message, agent=SkepticalCofounderAgent.name, structured=structured)
        return {"founder_message": message_view(founder_msg), "reply": message_view(reply), "status": session.status}

    def decide_negotiation(self, session: NegotiationSession, decision: str, expected_version: int, reason: str) -> dict[str, Any]:
        if session.status != "proposed" or not session.proposed_change:
            raise InvalidTransition("There is no proposed revision to decide on.")
        plan = self._plan_or_404()
        if decision == "approve" and plan.current_version != expected_version:
            session.status = "conflict"
            self.db.commit()
            raise VersionConflict(
                f"The plan moved to v{plan.current_version} after you opened this edit (v{expected_version}). Reopen the node to negotiate again.",
                current_version=plan.current_version, expected_version=expected_version)
        approval = approvals.record_decision(self.db, self.venture, subject_type="plan_revision", subject_id=session.id,
                                             decision=decision, actor="founder", reason=reason, audit=self.audit)
        if decision == "reject":
            session.status = "rejected"
            return {"decision": "reject", "plan_version": plan.current_version}
        revision = ProposedRevision.model_validate(session.proposed_change)
        version = plan_versioning.commit_revision(self.db, plan=plan, revision=revision, expected_version=expected_version, approval=approval)
        session.status = "approved"
        self.audit.record(self.db, venture_id=self.venture.id, agent="workflow", action=f"commit_plan_v{version.version}",
                          execution_mode="deterministic_rule", approved_by="founder",
                          detail={"node": session.node_id, "changes": len(revision.changes)})
        return {"decision": "approve", "plan_version": version.version}

    # --- gates -----------------------------------------------------------------------------------------

    def evaluate_gate(self, phase: int) -> GateDecision:
        self.require_state({PHASE_STATE[phase]}, f"evaluate the phase {phase} gate")
        result = gates.evaluate(self.db, self.venture, phase, self.profile())
        checks = [c.as_dict() for c in result.checks]
        decision = GateDecision(venture_id=self.venture.id, phase=phase, outcome=result.outcome.value, checks=checks,
                                reasoning=result.reasoning, evidence_basis=result.evidence_basis)
        self.db.add(decision)
        self.db.flush()
        self.audit.record(self.db, venture_id=self.venture.id, agent="gate", action=f"phase{phase}_gate", model=None,
                          execution_mode="deterministic_rule", outcome=result.outcome.value,
                          detail={"failed": [c["id"] for c in checks if not c["passed"]], "basis": result.evidence_basis})
        try:
            commentary = GatekeeperAgent().explain(self.ctx, phase=phase, outcome=result.outcome.value, checks=checks)
            decision.model_commentary = commentary.commentary + (
                "\n\nNext steps:\n" + "\n".join(f"- {s}" for s in commentary.suggested_next_steps) if commentary.suggested_next_steps else "")
        except AgentFailure as exc:
            decision.model_commentary = f"Commentary unavailable ({exc.message}). The outcome above does not depend on it."

        outcome = result.outcome.value
        if outcome == "GO" and phase < 6:
            self.move(GATE_TARGET[phase], actor="gate", reason=f"Phase {phase} gate: GO.")
        elif outcome == "PIVOT":
            self.move(S.PIVOT_REQUIRED, actor="gate", reason=f"Phase {phase} gate: PIVOT. {result.reasoning}")
        elif outcome == "STOP":
            self.move(S.STOPPED, actor="gate", reason=f"Phase {phase} gate: STOP. {result.reasoning}")
        self.save_artifact(phase, "gate_decision", f"Phase {phase} gate: {outcome}", "markdown",
                           renderers.gate_md(phase, PHASE_NAMES[phase], outcome, result.reasoning, result.evidence_basis, checks,
                                             decision.model_commentary, self.venture.mode),
                           [outcome], {"gate_decision_id": decision.id, "metrics": json.loads(json.dumps(result.metrics, default=str))})
        return decision

    # --- theme --------------------------------------------------------------------------------------------

    def theme(self) -> dict[str, Any]:
        plan = plan_versioning.get_plan(self.db, self.venture.id)
        if plan is not None:
            doc = plan_versioning.get_version(self.db, plan).data
            venture_node = next((n for n in doc["nodes"] if n["id"] == "venture"), {})
            texts = [(doc.get("product_category", ""), 3.0), (doc.get("one_liner", ""), 2.0), (doc.get("title", ""), 1.0),
                     (doc.get("target_customer", ""), 2.0), (venture_node.get("explanation", ""), 1.0)]
            return theme_for(texts, self.venture.state, f"approved plan v{plan.current_version}")
        proposal = self.db.scalars(select(BusinessProposal).where(BusinessProposal.venture_id == self.venture.id)
                                   .order_by(BusinessProposal.number.desc())).first()
        if proposal is not None and proposal.status != "rejected":
            d = proposal.data
            return theme_for([(d["product_category"], 3.0), (d["one_liner"], 2.0), (d["target_customer"], 2.0)],
                             self.venture.state, f"proposal #{proposal.number}")
        profile = self.profile()
        texts = [(profile.preferences.starting_idea, 1.0), (" ".join(profile.preferences.problems_of_interest), 1.0)]
        last = self.db.scalars(select(Message).join(Conversation).where(
            Conversation.venture_id == self.venture.id, Conversation.kind == "debate", Message.role == "founder")
            .order_by(Message.id.desc())).first()
        if last is not None:
            texts.append((last.content, 1.5))
        return theme_for(texts, self.venture.state, "discussion so far")
