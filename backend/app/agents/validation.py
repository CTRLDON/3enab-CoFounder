"""Validation Agent: Mom Test interview plan, Lean Canvas, riskiest assumptions, experiments."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import InterviewPlan, ValidationPack
from app.services.context import plan_context


class ValidationAgent(BaseAgent):
    name = "validation"
    prompt_file = "validation.md"
    tools = ("read:plan", "read:evidence_register")
    responsibility = "Design honest, measurable validation: interviews, Lean Canvas, hypotheses, experiments."

    def interview_plan(self, ctx: AgentContext, *, proposal: dict[str, Any]) -> InterviewPlan:
        content = (
            f"APPROVED PROPOSAL\n{proposal}\n\nWrite a Mom Test interview plan: questions about the customer's past "
            "behaviour and current workarounds, never about whether they would like or buy the idea. "
            "These are questions for real interviews; do not answer them."
        )
        return self.call(ctx, task="design_interviews", schema=InterviewPlan, user_content=content)

    def validation_pack(self, ctx: AgentContext, *, plan_document: dict[str, Any], evidence_summary: str) -> ValidationPack:
        content = (
            plan_context(plan_document)
            + f"\n\nEVIDENCE REGISTER SUMMARY\n{evidence_summary}\n\n"
            "Produce a Lean Canvas, the riskiest assumptions (most dangerous first, linked to node ids), landing page "
            "copy for a waitlist test (no testimonials, no urgency, no income claims), and at most two extra "
            "experiments. Targets must be declared before results exist."
        )
        return self.call(ctx, task="design_validation", schema=ValidationPack, user_content=content)
