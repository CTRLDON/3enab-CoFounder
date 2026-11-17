"""Agent base class.

An agent here is: a named responsibility + its own system prompt file (prompts/<role>.md) +
typed input context + a typed output schema + an explicit tool list + logging. Agents return data;
they cannot approve, transition state or write the plan. Those operations live in workflows/ and
are only reachable from founder-authenticated API routes or deterministic gate code.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import AgentFailure
from app.models import AgentRun, Venture
from app.services.audit_log import AuditLogger
from app.services.ollama_client import ModelGateway, ModelOutputError, ModelRequest, ModelUnavailableError
from app.services.safety import redact_unsafe_sentences

T = TypeVar("T", bound=BaseModel)


@dataclass
class AgentContext:
    db: Session
    venture: Venture
    gateway: ModelGateway
    audit: AuditLogger


@lru_cache(maxsize=32)
def _read_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Agent prompt missing: {path}")
    return path.read_text(encoding="utf-8").strip()


def _redact(value: Any, removed: list[str]) -> Any:
    if isinstance(value, str):
        cleaned, rules = redact_unsafe_sentences(value)
        removed.extend(rules)
        return cleaned
    if isinstance(value, list):
        return [_redact(item, removed) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, removed) for key, item in value.items()}
    return value


class BaseAgent:
    name: ClassVar[str]
    prompt_file: ClassVar[str]
    tools: ClassVar[tuple[str, ...]] = ()
    responsibility: ClassVar[str] = ""

    def system_prompt(self) -> str:
        prompts_dir = get_settings().prompts_dir
        shared = _read_prompt(prompts_dir / "shared_rules.md")
        own = _read_prompt(prompts_dir / self.prompt_file)
        return f"{own}\n\n{shared}"

    def call(
        self,
        ctx: AgentContext,
        *,
        task: str,
        schema: type[T],
        user_content: str,
        history: list[dict[str, str]] | None = None,
        script_turn: int = 0,
        sources: list[str] | None = None,
    ) -> T:
        request = ModelRequest(
            agent=self.name,
            task=task,
            system=self.system_prompt(),
            messages=[*(history or []), {"role": "user", "content": user_content}],
            script_turn=script_turn,
            scenario=ctx.venture.demo_scenario,
        )
        mode = ctx.gateway.execution_mode
        live_model = get_settings().active_model if mode.startswith("live") else None
        try:
            result = ctx.gateway.generate_structured(request, schema)
        except (ModelUnavailableError, ModelOutputError) as exc:
            ctx.db.add(
                AgentRun(venture_id=ctx.venture.id, agent=self.name, task=task, status="failed", model=live_model,
                         execution_mode=mode, error=str(exc)[:2000])
            )
            ctx.audit.record(
                ctx.db, venture_id=ctx.venture.id, agent=self.name, action=f"{task}:failed", execution_mode=mode,
                model=live_model, detail={"error": str(exc)[:500]},
            )
            ctx.db.commit()  # keep the failure on record even though the request fails
            unavailable = isinstance(exc, ModelUnavailableError)
            raise AgentFailure(
                f"The {self.name.replace('_', ' ')} agent could not complete '{task}': {exc}",
                agent=self.name,
                task=task,
                reason="model_unavailable" if unavailable else "invalid_model_output",
                retryable=True,
            ) from exc

        removed: list[str] = []
        cleaned = schema.model_validate(_redact(result.data.model_dump(mode="json"), removed))
        ctx.db.add(
            AgentRun(
                venture_id=ctx.venture.id, agent=self.name, task=task, status="succeeded", model=result.model,
                execution_mode=result.execution_mode, output=cleaned.model_dump(mode="json"),
                prompt_tokens=result.prompt_tokens, completion_tokens=result.completion_tokens,
                duration_ms=result.duration_ms, attempts=result.attempts,
            )
        )
        detail: dict[str, Any] = {"attempts": result.attempts}
        if result.prompt_tokens or result.completion_tokens:
            detail["tokens"] = {"prompt": result.prompt_tokens, "completion": result.completion_tokens}
        if removed:
            detail["policy_redactions"] = sorted(set(removed))
        ctx.audit.record(
            ctx.db, venture_id=ctx.venture.id, agent=self.name, action=task, execution_mode=result.execution_mode,
            model=result.model, sources=sources, cost=0.0, detail=detail,
        )
        return cleaned
