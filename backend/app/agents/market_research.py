"""Market Research Agent: turns the proposal into research questions, then retrieves evidence
through the research service (free public sources only). The model never writes evidence itself."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import ResearchPlan
from app.services.research_service import ResearchOutcome, ResearchService


class MarketResearchAgent(BaseAgent):
    name = "market_research"
    prompt_file = "market_research.md"
    tools = ("research:world_bank_indicators", "research:wikipedia_summary")
    responsibility = "Formulate research questions and gather sourced evidence without fabricating any."

    def plan(self, ctx: AgentContext, *, proposal: dict[str, Any], country: str) -> ResearchPlan:
        content = (
            f"APPROVED PROPOSAL\n{proposal}\n\nTARGET MARKET: {country or 'not stated'}\n\n"
            "Write up to six specific research questions. Use indicator_hint only when a national statistic "
            "(internet_users, gdp_per_capita, inflation, population) genuinely informs the question. List named "
            "alternatives customers might use (they will be checked against a retrieved source) and customer-problem "
            "hypotheses to test in interviews. Use node ids from: market, market-context, problems, core-problem, "
            "competitors, revenue, costs, primary-customer."
        )
        return self.call(ctx, task="plan_research", schema=ResearchPlan, user_content=content)

    def research(self, ctx: AgentContext, service: ResearchService, *, proposal: dict[str, Any], country: str) -> tuple[ResearchPlan, ResearchOutcome]:
        plan = self.plan(ctx, proposal=proposal, country=country)
        outcome = service.run(plan, country)
        ctx.audit.record(
            ctx.db,
            venture_id=ctx.venture.id,
            agent=self.name,
            action="retrieve_evidence",
            execution_mode="deterministic_tool",
            sources=sorted(set(outcome.sources_used)),
            model=None,
            detail={"records": len(outcome.evidence), "retrieval_available": outcome.retrieval_available, "notes": outcome.notes},
        )
        return plan, outcome
