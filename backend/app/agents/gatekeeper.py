"""Gatekeeper Agent: explains a gate decision that deterministic code already made.

The outcome (GO / REPEAT / PIVOT / STOP) comes from workflows/gates.py. The model's output schema has
no outcome field, so a favourable model response cannot turn a failed check into a pass."""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import AgentContext, BaseAgent
from app.schemas.agent_io import GateCommentary


class GatekeeperAgent(BaseAgent):
    name = "gatekeeper"
    prompt_file = "gatekeeper.md"
    tools = ("read:gate_checks",)
    responsibility = "Explain gate results and next steps. Cannot change outcomes."

    def explain(self, ctx: AgentContext, *, phase: int, outcome: str, checks: list[dict[str, Any]]) -> GateCommentary:
        content = (
            f"PHASE {phase} GATE — OUTCOME ALREADY DECIDED BY CODE: {outcome}\nCHECKS:\n{json.dumps(checks, indent=1)}\n\n"
            "Explain in plain language why the outcome follows from the failed or passed checks and what the founder "
            "should do next. Do not argue for a different outcome."
        )
        return self.call(ctx, task=f"explain_phase{phase}_gate_{outcome.lower()}", schema=GateCommentary, user_content=content)
