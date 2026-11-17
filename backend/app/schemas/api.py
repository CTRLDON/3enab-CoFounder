"""Request contracts for the HTTP API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import EvidenceClass


class VentureCreate(BaseModel):
    mode: Literal["live", "demo"] = "live"
    demo_scenario: Literal["main", "weak"] | None = None


class ChatMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(default="", max_length=1000)


class ReasonIn(BaseModel):
    reason: str = Field(default="", max_length=1000)


class NegotiationOpen(BaseModel):
    node_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


class NegotiationDecision(DecisionIn):
    expected_version: int = Field(ge=1)


class ApprovalIn(DecisionIn):
    subject_type: Literal["commercial_setup", "launch_package", "external_action", "support_reply"]
    subject_id: str | None = Field(default=None, max_length=120)


class ExperimentResultIn(BaseModel):
    observed: float = Field(ge=0, le=10_000_000)
    source: Literal["founder_reported", "mocked"] = "founder_reported"
    note: str = Field(default="", max_length=1000)
    evidence_url: HttpUrl | None = None


class EvidenceIn(BaseModel):
    claim: str = Field(min_length=3, max_length=2000)
    classification: EvidenceClass = EvidenceClass.ASSUMPTION
    source_url: HttpUrl | None = None
    source_title: str | None = Field(default=None, max_length=300)
    node_id: str | None = Field(default=None, max_length=64)
    limitations: str = Field(default="", max_length=1000)


class MockEventIn(BaseModel):
    event_id: str = Field(min_length=4, max_length=80, pattern=r"^[A-Za-z0-9_\-:.]+$")


class ExternalActionIn(BaseModel):
    kind: Literal["publish", "send", "spend", "sign"]
    target: str = Field(min_length=1, max_length=120)
    content: str = Field(default="", max_length=4000)


class SupportTicketIn(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    source: Literal["founder_entered", "mocked"] = "founder_entered"
