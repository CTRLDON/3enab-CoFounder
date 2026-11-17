"""Founder Discovery Agent: interprets the onboarding profile into strengths, limits and constraints."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import FounderInsights
from app.schemas.founder import FounderProfileData
from app.services.context import founder_context


class FounderDiscoveryAgent(BaseAgent):
    name = "founder_discovery"
    prompt_file = "founder_discovery.md"
    tools = ("read:founder_profile",)
    responsibility = "Interpret the founder's background, resources and constraints."

    def interpret(self, ctx: AgentContext, profile: FounderProfileData) -> FounderInsights:
        return self.call(
            ctx,
            task="interpret_founder_profile",
            schema=FounderInsights,
            user_content=founder_context(profile)
            + "\n\nIdentify the founder's real strengths, limitations, hard constraints, areas where they have an "
            "unfair advantage, and the most important open questions. Base everything on the profile only.",
        )
