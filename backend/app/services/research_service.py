"""Research pipeline: question -> retrieval from free public sources -> evidence draft.

Sources (keyless, free):
  * World Bank Indicators API  — country context (internet use, GDP per capita, inflation, population)
  * Wikipedia REST API          — confirms that a named competitor/alternative exists

What this service never does: invent competitors, statistics, market sizes or customer reviews.
When retrieval is impossible (offline, blocked, source down) every question is recorded as
UNKNOWN with the reason, and suggested sources to consult manually are attached instead.
Retrieved text is treated strictly as data (see safety.sanitize_external_text).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx

from app.config import Settings
from app.schemas.agent_io import ResearchPlan
from app.schemas.common import Confidence, EvidenceClass
from app.services.safety import sanitize_external_text

INDICATORS: dict[str, tuple[str, str]] = {
    "internet_users": ("IT.NET.USER.ZS", "Individuals using the Internet (% of population)"),
    "gdp_per_capita": ("NY.GDP.PCAP.CD", "GDP per capita (current US$)"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
    "population": ("SP.POP.TOTL", "Population, total"),
}

COUNTRY_CODES: dict[str, str] = {
    "egypt": "EG", "saudi arabia": "SA", "united arab emirates": "AE", "uae": "AE", "jordan": "JO",
    "morocco": "MA", "tunisia": "TN", "nigeria": "NG", "kenya": "KE", "south africa": "ZA",
    "united states": "US", "usa": "US", "united kingdom": "GB", "uk": "GB", "germany": "DE",
    "france": "FR", "canada": "CA", "india": "IN", "pakistan": "PK", "indonesia": "ID",
    "brazil": "BR", "turkey": "TR", "turkiye": "TR", "mexico": "MX", "spain": "ES", "italy": "IT",
}

# Context-dependent source preferences. Suggested for manual review; never cited as retrieved.
REGIONAL_SOURCES: dict[str, list[tuple[str, str]]] = {
    "EG": [
        ("CAPMAS — Central Agency for Public Mobilization and Statistics", "https://www.capmas.gov.eg/"),
        ("Central Bank of Egypt", "https://www.cbe.org.eg/"),
        ("GAFI — General Authority for Investment and Free Zones", "https://www.gafi.gov.eg/"),
        ("ITIDA — Information Technology Industry Development Agency", "https://itida.gov.eg/"),
        ("MCIT — Ministry of Communications and Information Technology", "https://mcit.gov.eg/"),
        ("World Bank data for Egypt", "https://data.worldbank.org/country/egypt-arab-rep"),
        ("IMF country page for Egypt", "https://www.imf.org/en/Countries/EGY"),
    ],
}
DEFAULT_SOURCES = [
    ("World Bank Open Data", "https://data.worldbank.org/"),
    ("IMF Data", "https://www.imf.org/en/Data"),
]


@dataclass
class EvidenceDraft:
    claim: str
    classification: EvidenceClass
    verification_status: str
    confidence: Confidence = Confidence.LOW
    source_url: str | None = None
    source_title: str | None = None
    published_at: str | None = None
    retrieved_at: datetime | None = None
    limitations: str = ""
    implication: str = ""
    research_question: str | None = None
    node_id: str | None = None


@dataclass
class ResearchOutcome:
    evidence: list[EvidenceDraft] = field(default_factory=list)
    retrieval_available: bool = True
    suggested_sources: list[tuple[str, str]] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def country_code(country: str) -> str | None:
    return COUNTRY_CODES.get(country.strip().lower()) if country else None


class ResearchService:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(
            timeout=settings.research_timeout_seconds,
            headers={"User-Agent": settings.research_user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    # --- retrieval primitives -------------------------------------------------------------

    def world_bank_indicator(self, iso2: str, hint: str) -> EvidenceDraft | None:
        code, name = INDICATORS[hint]
        api_url = f"https://api.worldbank.org/v2/country/{iso2}/indicator/{code}?format=json&mrnev=1"
        response = self.client.get(api_url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return None
        row = payload[1][0]
        value, year = row.get("value"), row.get("date")
        if value is None:
            return None
        country_name = (row.get("country") or {}).get("value", iso2)
        formatted = f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"
        return EvidenceDraft(
            claim=f"{name}, {country_name}: {formatted} ({year}).",
            classification=EvidenceClass.ESTIMATE,
            verification_status="retrieved",
            confidence=Confidence.MEDIUM,
            source_url=f"https://data.worldbank.org/indicator/{code}?locations={iso2}",
            source_title=f"World Bank Open Data — {name}",
            published_at=str(year) if year else None,
            retrieved_at=datetime.now(UTC),
            limitations="National aggregate published by the World Bank (often a modelled estimate). "
            "It describes the country, not demand for this product.",
            implication="Context only: it can bound assumptions about reach or purchasing power, "
            "but does not validate demand.",
        )

    def wikipedia_entity(self, name: str) -> EvidenceDraft | None:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(name.replace(' ', '_'))}"
        response = self.client.get(url)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        if data.get("type") == "disambiguation":
            return None
        extract, injected = sanitize_external_text(data.get("extract") or "", limit=400)
        page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page") or url
        limitations = "Wikipedia is a tertiary source: it confirms the alternative exists, not its market share or local presence."
        if injected:
            limitations += " Instruction-like text in the source was removed and ignored."
        return EvidenceDraft(
            claim=f"Alternative exists: {data.get('title', name)} — {extract}",
            classification=EvidenceClass.VERIFIED,
            verification_status="retrieved",
            confidence=Confidence.MEDIUM,
            source_url=page,
            source_title=f"Wikipedia — {data.get('title', name)}",
            published_at=(data.get("timestamp") or "")[:10] or None,
            retrieved_at=datetime.now(UTC),
            limitations=limitations,
            implication="Customers already have this option; the proposal must show why they would switch.",
        )

    # --- pipeline ---------------------------------------------------------------------------

    def run(self, plan: ResearchPlan, country: str) -> ResearchOutcome:
        iso2 = country_code(country)
        outcome = ResearchOutcome(suggested_sources=REGIONAL_SOURCES.get(iso2 or "", DEFAULT_SOURCES))
        online = self.settings.research_online

        for question in plan.questions:
            draft: EvidenceDraft | None = None
            failure = (
                "Live retrieval is disabled (RESEARCH_ONLINE=false)."
                if self.settings.research_online is False
                else "Live retrieval unavailable in this run (an earlier request to a source failed)."
            )
            if online and question.indicator_hint != "none" and iso2:
                try:
                    draft = self.world_bank_indicator(iso2, question.indicator_hint)
                    failure = "The World Bank API returned no value for this indicator."
                except (httpx.HTTPError, ValueError) as exc:
                    outcome.retrieval_available = False
                    online = False  # do not wait on further timeouts in this run
                    failure = f"Retrieval failed ({type(exc).__name__}); the source could not be reached."
            elif online and question.indicator_hint != "none" and not iso2:
                failure = f"No country code known for '{country}', so no indicator was retrieved."
            elif online:
                failure = "No free source in Mate's toolset can answer this question directly; it needs primary research."
            if draft:
                draft.research_question = question.question
                draft.node_id = question.related_node_id
                outcome.evidence.append(draft)
                if draft.source_url:
                    outcome.sources_used.append(draft.source_url)
            else:
                outcome.evidence.append(
                    EvidenceDraft(
                        claim=f"Open question: {question.question}",
                        classification=EvidenceClass.UNKNOWN,
                        verification_status="unresolved",
                        limitations=failure,
                        implication=question.why_it_matters,
                        research_question=question.question,
                        node_id=question.related_node_id,
                    )
                )

        for name in plan.competitor_candidates:
            entity: EvidenceDraft | None = None
            reason = "Not checked: live retrieval is unavailable in this run."
            if online:
                try:
                    entity = self.wikipedia_entity(name)
                    reason = "No matching Wikipedia article; existence not confirmed by a retrieved source."
                except (httpx.HTTPError, ValueError) as exc:
                    outcome.retrieval_available = False
                    online = False
                    reason = f"Retrieval failed ({type(exc).__name__})."
            if entity:
                entity.node_id = "competitors"
                outcome.evidence.append(entity)
                if entity.source_url:
                    outcome.sources_used.append(entity.source_url)
            else:
                outcome.evidence.append(
                    EvidenceDraft(
                        claim=f"Possible alternative named by the model: {name}",
                        classification=EvidenceClass.ASSUMPTION,
                        verification_status="unverified_model_suggestion",
                        limitations=reason,
                        implication="Treat as a lead to check by hand, not as a confirmed competitor.",
                        node_id="competitors",
                    )
                )

        for hypothesis in plan.customer_problem_hypotheses:
            outcome.evidence.append(
                EvidenceDraft(
                    claim=hypothesis,
                    classification=EvidenceClass.ASSUMPTION,
                    verification_status="needs_customer_interviews",
                    limitations="Generated hypothesis about customers. Only real interviews or experiments can support it.",
                    implication="Test in Mom Test interviews before building on it.",
                    node_id="problems",
                )
            )

        if not online or not outcome.retrieval_available:
            outcome.notes.append(
                "Degraded research mode: live retrieval was unavailable, so open questions are recorded as UNKNOWN "
                "and suggested sources are listed for manual review."
            )
        return outcome


def normalize_classification(
    classification: EvidenceClass,
    *,
    source_url: str | None,
    retrieved_by_system: bool,
    venture_mode: str,
) -> tuple[EvidenceClass, str | None]:
    """Enforce the evidence rules. Returns the allowed classification and a downgrade note.

    * VERIFIED / ESTIMATE need a source the system itself retrieved.
    * MOCKED is only allowed in demo ventures.
    """
    if classification in (EvidenceClass.VERIFIED, EvidenceClass.ESTIMATE):
        if not source_url:
            return EvidenceClass.ASSUMPTION, "Downgraded to ASSUMPTION: no source URL."
        if not retrieved_by_system:
            return EvidenceClass.ASSUMPTION, "Downgraded to ASSUMPTION: the source was supplied but not retrieved and checked by Mate."
    if classification == EvidenceClass.MOCKED and venture_mode != "demo":
        return EvidenceClass.ASSUMPTION, "MOCKED data is only allowed in demo ventures."
    return classification, None
