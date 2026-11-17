"""Launch Agent: store page, announcements and launch checklist — drafts only, never published."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import LaunchPack
from app.services.context import plan_context


class LaunchAgent(BaseAgent):
    name = "launch"
    prompt_file = "launch.md"
    tools = ("read:plan", "read:commercial_setup")
    responsibility = "Draft the store page, launch messages and checklist. Publishing stays with the founder."

    def prepare(self, ctx: AgentContext, *, plan_document: dict[str, Any], pricing: str) -> LaunchPack:
        content = (
            plan_context(plan_document)
            + f"\n\nAPPROVED PRICING\n{pricing}\n\n"
            "Draft a store page, up to four launch announcements written in the founder's own voice (to be posted "
            "by the founder after approval), a delivery message for buyers, and a launch checklist. No reviews, "
            "testimonials, user counts, urgency, scarcity or income claims."
        )
        return self.call(ctx, task="prepare_launch_package", schema=LaunchPack, user_content=content)
