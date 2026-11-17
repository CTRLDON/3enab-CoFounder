"""Skeptical Co-Founder Agent: debates the idea, drafts proposals, negotiates plan edits."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import DebateTurn, FounderInsights, NegotiationTurn, ProposalDraft
from app.schemas.founder import FounderProfileData
from app.services.context import founder_context, plan_context, transcript


class SkepticalCofounderAgent(BaseAgent):
    name = "skeptical_cofounder"
    prompt_file = "skeptical_cofounder.md"
    tools = ("read:founder_profile", "read:conversation", "read:plan")
    responsibility = "Challenge assumptions, compare alternatives, propose a direction and negotiate plan changes."

    @staticmethod
    def _grounding(profile: FounderProfileData, insights: dict[str, Any] | None) -> str:
        text = founder_context(profile)
        if insights:
            text += "\n\nFOUNDER ANALYSIS (from the Founder Discovery agent)\n" + json.dumps(insights)[:2000]
        return text

    def debate_turn(
        self,
        ctx: AgentContext,
        *,
        profile: FounderProfileData,
        insights: dict[str, Any] | None,
        history: list[dict[str, Any]],
        founder_message: str,
        turn: int,
    ) -> DebateTurn:
        content = (
            self._grounding(profile, insights)
            + "\n\nFOUNDER'S LATEST MESSAGE\n"
            + founder_message
            + "\n\nRespond as the skeptical co-founder. Ask at most one key question. Classify every assumption. "
            "Update the readiness checklist honestly; set recommend_proposal only when a testable direction exists."
        )
        return self.call(ctx, task="debate_turn", schema=DebateTurn, user_content=content,
                         history=transcript(history), script_turn=turn)

    def draft_proposal(
        self,
        ctx: AgentContext,
        *,
        profile: FounderProfileData,
        insights: dict[str, Any] | None,
        history: list[dict[str, Any]],
        rejected: list[dict[str, Any]],
        number: int,
    ) -> ProposalDraft:
        rejected_text = "\n".join(
            f"- Proposal #{r['number']} '{r['business_name']}' was rejected: {r['reason']}" for r in rejected
        ) or "- none"
        content = (
            self._grounding(profile, insights)
            + f"\n\nPREVIOUSLY REJECTED PROPOSALS\n{rejected_text}\n\n"
            "Write the business proposal for the direction the discussion supports. Use the founder's currency for "
            "money. Every number is an ASSUMPTION unless a source was retrieved. List missing evidence honestly. "
            "If the evidence says not to proceed, set recommendation to DO_NOT_PROCEED and say why."
        )
        return self.call(ctx, task="draft_proposal", schema=ProposalDraft, user_content=content,
                         history=transcript(history), script_turn=number - 1)

    def negotiate(
        self,
        ctx: AgentContext,
        *,
        plan_document: dict[str, Any],
        node_id: str,
        history: list[dict[str, Any]],
        founder_message: str,
        turn: int,
    ) -> NegotiationTurn:
        content = (
            plan_context(plan_document, focus_node=node_id)
            + "\n\nTHE FOUNDER WANTS TO CHANGE THE FOCUS NODE\n"
            + founder_message
            + "\n\nAnalyse the change against the accepted strategy, customers, willingness to pay, costs and other "
            "affected nodes. Agree, disagree or counter-propose with reasons. Only when a mutually acceptable "
            "revision exists, set ready_to_propose and fill revision.changes using existing node ids and editable "
            "fields. You cannot apply the change; the founder must approve it."
        )
        return self.call(ctx, task="negotiate_node_edit", schema=NegotiationTurn, user_content=content,
                         history=transcript(history), script_turn=turn)
