"""Product Architect Agent: scopes the MVP inside the supported product class."""

from __future__ import annotations

from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import ProductSpec
from app.services.context import plan_context
from app.services.mvp_template import SUPPORTED_CAPABILITIES


class ProductArchitectAgent(BaseAgent):
    name = "product_architect"
    prompt_file = "product_architect.md"
    tools = ("read:plan", "read:validation_results")
    responsibility = "Define MVP scope, features, user journeys and acceptance criteria."

    def specify(self, ctx: AgentContext, *, plan_document: dict[str, Any], validation_summary: str) -> ProductSpec:
        content = (
            plan_context(plan_document)
            + f"\n\nVALIDATION SUMMARY\n{validation_summary}\n\n"
            "Specify the smallest MVP that tests the value proposition. The only product class Mate can build is an "
            "offline single-page records tool (one record type with typed fields and statuses). Allowed capabilities: "
            + ", ".join(sorted(SUPPORTED_CAPABILITIES))
            + ". Anything else the product would eventually need goes in out_of_scope."
        )
        return self.call(ctx, task="specify_mvp", schema=ProductSpec, user_content=content)
