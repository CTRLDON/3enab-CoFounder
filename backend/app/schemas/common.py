"""Shared enumerations used by agents, the API and the gates."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvidenceClass(StrEnum):
    VERIFIED = "VERIFIED"  # supported by a retrieved, identifiable source
    ESTIMATE = "ESTIMATE"  # a sourced third-party estimate
    ASSUMPTION = "ASSUMPTION"  # unverified proposition
    PROJECTION = "PROJECTION"  # modelled future scenario
    MOCKED = "MOCKED"  # artificial demo / test data
    UNKNOWN = "UNKNOWN"  # cannot currently be established


class EconomicClass(StrEnum):
    REVENUE = "revenue"
    EXPENSE = "expense"
    MIXED = "mixed"
    STRATEGIC = "strategic"
    UNKNOWN = "unknown"


class GateOutcome(StrEnum):
    GO = "GO"
    REPEAT = "REPEAT"
    PIVOT = "PIVOT"
    STOP = "STOP"


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MoneyEstimate(BaseModel):
    amount: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    period: str = Field(default="one-time", max_length=40)
    classification: EvidenceClass = EvidenceClass.ASSUMPTION
    basis: str = Field(default="", max_length=400)
