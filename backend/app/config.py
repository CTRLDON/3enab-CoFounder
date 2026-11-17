"""Centralised configuration. Every setting can be overridden through environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    # Model gateway. "gemini" = Google Gemini API free tier (needs GEMINI_API_KEY);
    # "ollama" = local open-weight model through Ollama.
    model_provider: Literal["gemini", "ollama"] = "gemini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com"
    gemini_timeout_seconds: float = 120.0
    gemini_max_retries: int = 2
    # 0 turns "thinking" off for speed and quota; -1 leaves the model's default.
    gemini_thinking_budget: int = 0
    # Free-tier rate limits (HTTP 429): how many times to wait and retry before reporting failure.
    gemini_rate_limit_retries: int = 2
    gemini_max_rate_limit_wait_seconds: float = 60.0

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"
    ollama_timeout_seconds: float = 240.0
    ollama_max_retries: int = 2
    ollama_think: bool = False
    ollama_temperature: float = 0.4

    # Application
    mate_default_mode: Literal["live", "demo"] = "live"
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'mate.db'}"
    decision_log_path: Path = REPO_ROOT / "data" / "decision_log.json"
    artifacts_dir: Path = REPO_ROOT / "data" / "artifacts"
    prompts_dir: Path = REPO_ROOT / "prompts"
    cors_origins: str = "http://localhost:8080,http://localhost:5173"

    # Research
    research_online: bool = True
    research_timeout_seconds: float = 8.0
    research_user_agent: str = "MateResearchBot/0.1 (open-source hackathon project)"

    # MVP build sandbox
    node_binary: str = "node"
    mvp_test_timeout_seconds: float = 60.0

    # Hard-coded policy: these are not configurable on purpose.
    @property
    def external_actions_enabled(self) -> bool:
        """No connector for publishing, sending, spending or payments exists in this build."""
        return False

    @property
    def payments_mode(self) -> str:
        return "MOCKED"

    @property
    def active_model(self) -> str:
        return self.gemini_model if self.model_provider == "gemini" else self.ollama_model

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
