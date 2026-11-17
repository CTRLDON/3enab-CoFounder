"""Founder profile collected during onboarding; becomes structured context for agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FounderBackground(BaseModel):
    education: str = Field(default="", max_length=600)
    skills: list[str] = Field(default_factory=list, max_length=30)
    experience: str = Field(default="", max_length=1200)
    entrepreneurial_experience: str = Field(default="", max_length=800)
    industries: list[str] = Field(default_factory=list, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=20)


class FounderResources(BaseModel):
    budget_amount: float | None = Field(default=None, ge=0, le=1_000_000_000)
    budget_currency: str = Field(default="USD")
    weekly_hours: float | None = Field(default=None, ge=0, le=100)
    technical_resources: str = Field(default="", max_length=600)
    business_contacts: str = Field(default="", max_length=600)
    customer_access: str = Field(default="", max_length=600)
    team: str = Field(default="", max_length=600)
    existing_assets: str = Field(default="", max_length=600)

    @field_validator("budget_currency")
    @classmethod
    def _currency_code(cls, value: str) -> str:
        code = value.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError("Use a three-letter currency code such as EGP or USD.")
        return code


class FounderPreferences(BaseModel):
    has_idea: bool = True
    starting_idea: str = Field(default="", max_length=2000)
    problems_of_interest: list[str] = Field(default_factory=list, max_length=15)
    target_country: str = Field(default="", max_length=80)
    preferred_audience: str = Field(default="", max_length=300)
    business_type: Literal["B2B", "B2C", "either"] = "either"
    risk_tolerance: Literal["low", "medium", "high"] = "medium"
    short_term_goal: str = Field(default="", max_length=600)
    long_term_goal: str = Field(default="", max_length=600)
    values_and_constraints: str = Field(default="", max_length=1000)


class FounderProfileData(BaseModel):
    background: FounderBackground = Field(default_factory=FounderBackground)
    resources: FounderResources = Field(default_factory=FounderResources)
    preferences: FounderPreferences = Field(default_factory=FounderPreferences)


class FounderCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    profile: FounderProfileData = Field(default_factory=FounderProfileData)

    @field_validator("display_name")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Tell Mate what to call you.")
        return value


class FounderOut(BaseModel):
    id: str
    display_name: str
    profile: FounderProfileData
    profile_revision: int


class FounderCreated(FounderOut):
    founder_token: str = Field(description="Session secret for this founder. Send as X-Founder-Token.")
