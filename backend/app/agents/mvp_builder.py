"""MVP Builder Agent: writes user-facing copy, then renders and tests the template-driven MVP.

The model contributes copy only. Code comes from reviewed templates (services/mvp_template.py) and
is checked by generated tests that run under a fixed command."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent
from app.config import get_settings
from app.schemas.agent_io import MvpCopy, ProductSpec
from app.services.mvp_template import BuildResult, build_mvp


class MvpBuilderAgent(BaseAgent):
    name = "mvp_builder"
    prompt_file = "mvp_builder.md"
    tools = ("template:records_tool", "sandbox:node_test")
    responsibility = "Render a constrained, testable MVP and its user documentation."

    def write_copy(self, ctx: AgentContext, *, spec: ProductSpec) -> MvpCopy:
        content = (
            f"PRODUCT SPEC\n{spec.model_dump_json()}\n\nWrite the app title, a plain tagline, the empty-state text, "
            "2-6 getting-started steps for a first-time user, and a privacy note stating that data stays in the browser."
        )
        return self.call(ctx, task="write_mvp_copy", schema=MvpCopy, user_content=content)

    def build(self, ctx: AgentContext, *, spec: ProductSpec, copy: MvpCopy, accent: str) -> BuildResult:
        settings = get_settings()
        result = build_mvp(spec, copy, node_binary=settings.node_binary, timeout=settings.mvp_test_timeout_seconds, accent=accent)
        ctx.audit.record(
            ctx.db,
            venture_id=ctx.venture.id,
            agent=self.name,
            action="render_and_test_mvp",
            execution_mode="deterministic_tool",
            model=None,
            detail={
                "files": sorted(result.files),
                "tests_executed": result.test_executed,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
                "exit_code": result.exit_code,
            },
        )
        return result
