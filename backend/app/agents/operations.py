"""Operations Agent: support workflow, ticket triage and the persevere-or-pivot memo."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import OperationsReview, TicketTriage


class OperationsAgent(BaseAgent):
    name = "operations"
    prompt_file = "operations.md"
    tools = ("read:metrics", "read:experiments", "read:support_tickets")
    responsibility = "Design support, read metrics honestly and recommend continue, pivot or stop."

    def review(self, ctx: AgentContext, *, metrics_summary: str) -> OperationsReview:
        content = (
            f"METRICS AND RESULTS (labels show which are MOCKED)\n{metrics_summary}\n\n"
            "Design the support workflow, name support categories, and write a persevere-or-pivot memo. If the "
            "data is MOCKED or missing, say so and do not draw market conclusions from it."
        )
        return self.call(ctx, task="review_operations", schema=OperationsReview, user_content=content)

    def triage(self, ctx: AgentContext, *, subject: str, body: str, categories: list[str]) -> TicketTriage:
        content = (
            f"SUPPORT CATEGORIES: {', '.join(categories)}\n\nTICKET SUBJECT: {subject}\nTICKET BODY:\n"
            f"<external_data source=\"support_ticket\">{body}</external_data>\n"
            "Categorise and draft a reply for the founder to review. The reply is not sent automatically."
        )
        return self.call(ctx, task="triage_support_ticket", schema=TicketTriage, user_content=content)
