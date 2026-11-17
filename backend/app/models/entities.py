"""Relational data model.

Structured documents (founder profile, proposal, plan version) are stored as validated JSON
inside relational rows; everything that needs querying, approval or auditing is its own table.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex[:16]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# --- Founder -----------------------------------------------------------------------------


class Founder(TimestampMixin, Base):
    __tablename__ = "founders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(120))
    token_hash: Mapped[str] = mapped_column(String(64), index=True)
    profile: Mapped[FounderProfile] = relationship(back_populates="founder", uselist=False)


class FounderProfile(Base):
    __tablename__ = "founder_profiles"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    founder_id: Mapped[str] = mapped_column(ForeignKey("founders.id"), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    founder: Mapped[Founder] = relationship(back_populates="profile")


# --- Venture and state ---------------------------------------------------------------------


class Venture(TimestampMixin, Base):
    __tablename__ = "ventures"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    founder_id: Mapped[str] = mapped_column(ForeignKey("founders.id"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Untitled venture")
    state: Mapped[str] = mapped_column(String(40))
    mode: Mapped[str] = mapped_column(String(10))  # live | demo
    demo_scenario: Mapped[str | None] = mapped_column(String(40), nullable=True)
    founder_insights: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StateTransition(TimestampMixin, Base):
    __tablename__ = "state_transitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    from_state: Mapped[str] = mapped_column(String(40))
    to_state: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(60))
    reason: Mapped[str] = mapped_column(Text)


# --- Conversations -------------------------------------------------------------------------


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # debate | negotiation
    messages: Mapped[list[Message]] = relationship(order_by="Message.seq", cascade="all, delete-orphan")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))  # founder | agent | system
    agent: Mapped[str | None] = mapped_column(String(60), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    structured: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


# --- Proposal, approval, plan --------------------------------------------------------------


class BusinessProposal(TimestampMixin, Base):
    __tablename__ = "proposals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20))  # awaiting | approved | rejected | superseded
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FounderApproval(TimestampMixin, Base):
    """An explicit founder decision. The only way gated actions become 'approved'."""

    __tablename__ = "founder_approvals"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    subject_type: Mapped[str] = mapped_column(String(40))
    subject_id: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(10))  # approve | reject
    actor: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(Text, default="")


class BusinessPlan(TimestampMixin, Base):
    __tablename__ = "business_plans"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), unique=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("proposals.id"))
    current_version: Mapped[int] = mapped_column(Integer, default=1)


class PlanVersion(TimestampMixin, Base):
    __tablename__ = "plan_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("business_plans.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict[str, Any]] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(60))
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("founder_approvals.id"), nullable=True)


class NodeRevision(TimestampMixin, Base):
    __tablename__ = "node_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(ForeignKey("business_plans.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(64), index=True)
    from_version: Mapped[int] = mapped_column(Integer)
    to_version: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    approved_by: Mapped[str] = mapped_column(String(40))


class NegotiationSession(TimestampMixin, Base):
    __tablename__ = "negotiation_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(64))
    base_version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # open | proposed | approved | rejected | conflict
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    proposed_change: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


# --- Evidence and validation ---------------------------------------------------------------


class EvidenceRecord(TimestampMixin, Base):
    __tablename__ = "evidence_records"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    claim: Mapped[str] = mapped_column(Text)
    classification: Mapped[str] = mapped_column(String(20))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[str] = mapped_column(String(10), default="low")
    limitations: Mapped[str] = mapped_column(Text, default="")
    implication: Mapped[str] = mapped_column(Text, default="")
    research_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypothesis_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str] = mapped_column(String(60))


class Hypothesis(TimestampMixin, Base):
    __tablename__ = "hypotheses"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    statement: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(10))  # high | medium | low
    node_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="untested")


class ValidationExperiment(TimestampMixin, Base):
    __tablename__ = "validation_experiments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    hypothesis_id: Mapped[str | None] = mapped_column(ForeignKey("hypotheses.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    method: Mapped[str] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(120))
    target: Mapped[float] = mapped_column(Float)
    window_days: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[list[ExperimentResult]] = relationship(order_by="ExperimentResult.id")


class ExperimentResult(TimestampMixin, Base):
    __tablename__ = "experiment_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("validation_experiments.id"), index=True)
    observed: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))  # founder_reported | mocked
    note: Mapped[str] = mapped_column(Text, default="")
    evidence_url: Mapped[str | None] = mapped_column(Text, nullable=True)


# --- Agents, gates, artifacts, audit -------------------------------------------------------


class AgentRun(TimestampMixin, Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str | None] = mapped_column(ForeignKey("ventures.id"), nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String(60))
    task: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20))  # succeeded | failed
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=1)


class GateDecision(TimestampMixin, Base):
    __tablename__ = "gate_decisions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    phase: Mapped[int] = mapped_column(Integer)
    outcome: Mapped[str] = mapped_column(String(10))  # GO | REPEAT | PIVOT | STOP
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    reasoning: Mapped[str] = mapped_column(Text)
    evidence_basis: Mapped[str] = mapped_column(String(20))
    model_commentary: Mapped[str | None] = mapped_column(Text, nullable=True)


class GeneratedArtifact(TimestampMixin, Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    phase: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    content_type: Mapped[str] = mapped_column(String(40))  # markdown | json | html | bundle
    content: Mapped[str] = mapped_column(Text)
    labels: Mapped[list[str]] = mapped_column(JSON, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuditEvent(Base):
    """One row per agent action or important transition; mirrors decision_log.json."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venture_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    agent: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(120))
    sources: Mapped[list[str]] = mapped_column(JSON, default=list)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    approved_by: Mapped[str | None] = mapped_column(String(40), nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True)
    execution_mode: Mapped[str] = mapped_column(String(20))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# --- MOCKED commerce -----------------------------------------------------------------------


class MockOrder(TimestampMixin, Base):
    __tablename__ = "mock_orders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    buyer_label: Mapped[str] = mapped_column(String(80))  # synthetic, e.g. "synthetic-buyer-1"
    product_sku: Mapped[str] = mapped_column(String(80))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))
    status: Mapped[str] = mapped_column(String(30))  # mock_paid | mock_refunded
    approval_id: Mapped[str] = mapped_column(ForeignKey("founder_approvals.id"))


class MockEntitlement(TimestampMixin, Base):
    __tablename__ = "mock_entitlements"
    __table_args__ = (UniqueConstraint("order_id"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    order_id: Mapped[str] = mapped_column(ForeignKey("mock_orders.id"))
    access_key: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))  # active | revoked
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MockEventReceipt(TimestampMixin, Base):
    """Processed mock events, keyed for idempotency (the same event never runs twice)."""

    __tablename__ = "mock_event_receipts"
    event_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("mock_orders.id"))
    kind: Mapped[str] = mapped_column(String(30))
    result: Mapped[dict[str, Any]] = mapped_column(JSON)


class MockLedgerEntry(TimestampMixin, Base):
    __tablename__ = "mock_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("mock_orders.id"))
    kind: Mapped[str] = mapped_column(String(20))  # charge | fee | refund | payout
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8))


class SupportTicket(TimestampMixin, Base):
    __tablename__ = "support_tickets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    venture_id: Mapped[str] = mapped_column(ForeignKey("ventures.id"), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20))  # founder_entered | mocked
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    draft_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open")
