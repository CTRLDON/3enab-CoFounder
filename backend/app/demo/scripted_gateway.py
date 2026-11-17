"""Offline demo gateway: returns scripted fixtures through the same validation path as live output."""

from __future__ import annotations

from pydantic import ValidationError

from app.demo.scenarios import scripted_response
from app.services.ollama_client import SCRIPTED_MODE, ModelOutputError, ModelRequest, ModelResult, T


class ScriptedDemoGateway:
    execution_mode = SCRIPTED_MODE

    def generate_structured(self, request: ModelRequest, schema: type[T]) -> ModelResult[T]:
        fixture = scripted_response(request.scenario or "main", request.agent, request.task, request.script_turn)
        if fixture is None:
            raise ModelOutputError(
                f"Scripted demo has no response for {request.agent}/{request.task}. Use a live venture for this step."
            )
        try:
            data = schema.model_validate(fixture)
        except ValidationError as exc:  # a broken fixture is a bug; surface it
            raise ModelOutputError(f"Scripted fixture for {request.agent}/{request.task} is invalid: {exc}") from exc
        return ModelResult(data=data, model=None, execution_mode=SCRIPTED_MODE)
