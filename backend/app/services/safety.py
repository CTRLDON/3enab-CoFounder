"""Programmatic policy guard.

These checks run in code, before and after every model call, so prompts are never the only line
of defence. They distinguish manipulation (fabricating reviews, sign-ups, urgency; impersonation;
payments; credential storage; unapproved external actions; attempts to override gates) from
legitimate work such as analysing competitors' public reviews.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_F = re.IGNORECASE


@dataclass(frozen=True)
class SafetyFinding:
    kind: str  # prohibited_category | manipulation | override_attempt | unsafe_claim | injection
    rule: str
    message: str
    matched: str = ""


@dataclass
class SafetyReport:
    findings: list[SafetyFinding] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.findings)

    def kinds(self) -> set[str]:
        return {f.kind for f in self.findings}

    def rules(self) -> list[str]:
        return [f.rule for f in self.findings]


# --- Excluded product categories (hackathon rules) -------------------------------------------------

PROHIBITED_CATEGORIES: dict[str, tuple[str, list[re.Pattern[str]]]] = {
    "physical_goods": (
        "Physical goods are out of scope: Mate only builds digital products.",
        [
            re.compile(r"\b(sell(ing)?|ship(ping)?|stock(ing)?|import(ing)?)\s+(physical|handmade|printed)\s+\w+", _F),
            re.compile(r"\bphysical\s+(goods|products?|merchandise|items)\b", _F),
            re.compile(r"\b(drop[- ]?shipping|print[- ]on[- ]demand)\b", _F),
            re.compile(r"\bsell(ing)?\s+(t-?shirts|clothes|clothing|shoes|furniture|jewel(le)?ry|cosmetics|food|coffee|candles)\b", _F),
        ],
    ),
    "financial_products": (
        "Financial and investment products are out of scope.",
        [
            re.compile(r"\b(investment|investing|trading|stock|forex|options)\s+(advice|signals?|tips|bot|platform|app|recommendations?)\b", _F),
            re.compile(r"\b(robo[- ]?advis[eo]r|peer[- ]to[- ]peer lending|payday loans?|micro[- ]?loans?|lending (app|platform))\b", _F),
            re.compile(r"\b(personal finance|financial|wealth)\s+advice\b", _F),
            re.compile(r"\binsurance (product|policies|app)\b", _F),
        ],
    ),
    "crypto": (
        "Crypto products are out of scope.",
        [
            re.compile(r"\b(crypto(currenc(y|ies))?|bitcoin|ethereum|memecoins?|nfts?|defi|token sale|ico)\b", _F),
        ],
    ),
    "health_advice": (
        "Health-advice products are out of scope.",
        [
            re.compile(r"\b(medical|health|clinical|nutrition(al)?|diet(ary)?|mental[- ]health)\s+(advice|diagnos\w*|consultations?|coach(ing)?|recommendations?)\b", _F),
            re.compile(r"\bsymptom[- ]?checker\b", _F),
            re.compile(r"\b(medication|drug)\s+dosage\b", _F),
            re.compile(r"\b(ai|virtual)\s+(doctor|therapist|nutritionist)\b", _F),
        ],
    ),
    "legal_advice": (
        "Legal-advice products are out of scope.",
        [
            re.compile(r"\blegal\s+(advice|counsel|consultations?|opinions?)\b", _F),
            re.compile(r"\b(ai|virtual|robot)\s+lawyer\b", _F),
            re.compile(r"\blawyer[- ]?bot\b", _F),
            re.compile(r"\b(draft|write)\s+(contracts|wills|lawsuits)\s+for\s+(clients|customers|users|people)\b", _F),
        ],
    ),
}

# --- Manipulation and forbidden actions ----------------------------------------------------------

_CREATE_VERB = r"(write|generate|create|make|produce|fabricate|invent|post|give me|draft|add)"
_QUALIFIER = re.compile(
    r"\b(fake|five[- ]star|5[- ]star|positive|glowing|\d+|a few|some|several|dozens?|hundreds?|one|two|three|four|five|ten|twenty|fifty)\b"
    r"|\bfrom\s+(happy|satisfied|real-sounding|our)\s+(customers|users|clients|students)\b",
    _F,
)
_TESTIMONIAL_REQUEST = re.compile(_CREATE_VERB + r"\b[^.?!\n]{0,60}\btestimonials?\b", _F)
_REVIEW_REQUEST = re.compile(_CREATE_VERB + r"\b[^.?!\n]{0,60}\b(reviews?|testimonials?|ratings?|endorsements?)\b", _F)
_REVIEW_LEGIT = re.compile(
    r"\b(analy[sz]e|summari[sz]e|read|study|research)\b[^.?!\n]{0,40}\breviews?\b"
    r"|\b(reviews?|testimonials?)\s+from\s+(real|actual|verified)\b"
    r"|\b(ask|collect|request|gather)\b[^.?!\n]{0,40}\b(honest\s+)?(reviews?|feedback|testimonials?)\b",
    _F,
)

MANIPULATION_RULES: list[tuple[str, str, list[re.Pattern[str]]]] = [
    (
        "fake_signups",
        "Mate will not invent sign-ups, users, traction or results. Only recorded results count.",
        [
            re.compile(r"\b(fake|fabricate|invent|inflate|pad|make up|made[- ]up)\b[^.?!\n]{0,40}\b(sign[- ]?ups?|waitlist|subscribers|users|numbers|metrics|traction|results|data)\b", _F),
            re.compile(r"\b(add|generate|create)\b[^.?!\n]{0,30}\b(fake|bot|dummy)\s+(users|accounts|sign[- ]?ups?)\b", _F),
            re.compile(r"\bpretend\b[^.?!\n]{0,40}\b(hit|reached|met|got)\b[^.?!\n]{0,30}\b(target|goal|sign[- ]?ups?)\b", _F),
        ],
    ),
    (
        "fake_urgency",
        "Mate will not create fake urgency, scarcity or countdown timers.",
        [
            re.compile(r"\b(fake|false|artificial|manufactured)\s+(urgency|scarcity|deadline|countdown)\b", _F),
            re.compile(r"\bcountdown\s+timers?\b", _F),
        ],
    ),
    (
        "impersonation",
        "Mate will not pose as the founder, a customer or another brand.",
        [
            re.compile(r"\b(pretend(ing)?\s+to\s+be|pos(e|ing)\s+as|impersonat\w+)\b", _F),
            re.compile(r"\b(as\s+if\s+(it|they|these)\s+(came|were|was)\s+from)\b", _F),
        ],
    ),
    (
        "guaranteed_income",
        "Mate never promises income or success.",
        [
            re.compile(r"\bguarantee(d|s)?\b[^.?!\n]{0,40}\b(income|revenue|profits?|success|money|returns|sales|earnings)\b", _F),
            re.compile(r"\b(get rich|risk[- ]free (income|profits?|returns))\b", _F),
        ],
    ),
    (
        "credential_storage",
        "Mate does not store passwords, card numbers or bank details.",
        [
            re.compile(r"\b(store|save|keep|remember|collect)\b[^.?!\n]{0,40}\b(passwords?|credentials|card numbers?|credit cards?|cvv|bank (account|details)|iban)\b", _F),
        ],
    ),
    (
        "payment_processing",
        "No payments of any kind run in Mate, not even sandbox payments. Checkout is MOCKED.",
        [
            re.compile(r"\b(integrat\w*|connect\w*|set\s*up|hook\s+up|wire\s+up|add|use)\b[^.?!\n]{0,30}\b(stripe|paypal|paymob|fawry|braintree|adyen)\b", _F),
            re.compile(r"\b(stripe|paypal|paymob|fawry|braintree|adyen)\b[^.?!\n]{0,30}\b(integration|checkout|api|keys?|sandbox|test mode|account)\b", _F),
            re.compile(r"\b(charge|bill)\s+(the\s+|my\s+|their\s+)?(customers?|cards?|buyers?|users?)\b", _F),
            re.compile(r"\b(process|take|accept|collect)\s+(real\s+|live\s+|sandbox\s+)?payments?\b", _F),
        ],
    ),
    (
        "unapproved_external_action",
        "Nothing is published, sent or spent without explicit founder approval, and external connectors are disabled in this build.",
        [
            re.compile(r"\b(post|publish|tweet|send|email|spend|buy\s+ads|launch\s+ads)\b[^.?!\n]{0,50}\b(without\s+(asking|approval|me|checking)|automatically\s+to)\b", _F),
            re.compile(r"\bcreate\s+(an?\s+)?accounts?\s+(on|for\s+me\s+on)\b", _F),
        ],
    ),
]

OVERRIDE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bignore\s+(all\s+|the\s+|your\s+|any\s+)?(previous|prior|above|earlier)?\s*(instructions|rules|guidelines|prompts?)\b", _F),
    re.compile(r"\b(mark|set|label|flag|declare)\b[^.?!\n]{0,40}\b(as\s+)?(validated|verified|approved|passed)\b", _F),
    re.compile(r"\b(skip|bypass|override|disable)\b[^.?!\n]{0,30}\b(gate|gates|approval|validation|checks?)\b", _F),
    re.compile(r"\b(you are now|new system prompt|developer mode|act as (an? )?unrestricted)\b", _F),
]

UNSAFE_OUTPUT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("guaranteed_income", re.compile(r"\bguarantee(d|s)?\b[^.?!\n]{0,40}\b(income|revenue|profits?|success|returns|sales|earnings)\b", _F)),
    ("guaranteed_income", re.compile(r"\byou(\s+will|'ll)\s+(definitely\s+|surely\s+)?(make|earn)\s+[$€£]?\s?\d", _F)),
    ("fake_urgency", re.compile(r"\b(only\s+\d+\s+(left|spots|seats|copies)|offer\s+ends\s+(tonight|today|soon|in\s+\d+)|hurry|act\s+now|limited\s+time\s+only)\b", _F)),
    ("fake_testimonial", re.compile(r"[\"“][^\"”]{10,200}[\"”]\s*[—–-]\s*[A-Z][a-z]+(,|\s)\s*(a\s+)?(happy\s+|satisfied\s+)?(customer|user|student|owner|client)", _F)),
    ("fake_testimonial", re.compile(r"\b(\d[\d,]*\+?\s+(happy|satisfied)\s+(customers|users|students|clients))\b", _F)),
]

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    *OVERRIDE_PATTERNS,
    re.compile(r"\b(system|assistant)\s*:\s", _F),
    re.compile(r"<\s*/?\s*(system|instructions?)\s*>", _F),
]


def _first_match(patterns: list[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def screen_venture_category(text: str) -> SafetyReport:
    report = SafetyReport()
    for rule, (message, patterns) in PROHIBITED_CATEGORIES.items():
        matched = _first_match(patterns, text)
        if matched:
            report.findings.append(SafetyFinding("prohibited_category", rule, message, matched))
    return report


def _fake_review_request(text: str) -> str | None:
    if re.search(r"\bfake\s+(reviews?|testimonials?|ratings?)\b", text, _F):
        return "fake reviews"
    for sentence in re.split(r"(?<=[.?!\n])\s+", text):
        testimonial = _TESTIMONIAL_REQUEST.search(sentence)
        if testimonial and not _REVIEW_LEGIT.search(sentence):
            return testimonial.group(0)  # Mate writing a testimonial is always fabrication
        match = _REVIEW_REQUEST.search(sentence)
        if match and _QUALIFIER.search(sentence) and not _REVIEW_LEGIT.search(sentence):
            return match.group(0)
    return None


def screen_founder_message(text: str) -> SafetyReport:
    """Run on every founder message before any model sees it."""
    report = screen_venture_category(text)
    fake_review = _fake_review_request(text)
    if fake_review:
        report.findings.append(
            SafetyFinding(
                "manipulation",
                "fake_reviews",
                "Mate will not write reviews or testimonials. It can help you collect honest feedback from real users.",
                fake_review,
            )
        )
    for rule, message, patterns in MANIPULATION_RULES:
        matched = _first_match(patterns, text)
        if matched:
            report.findings.append(SafetyFinding("manipulation", rule, message, matched))
    matched_override = _first_match(OVERRIDE_PATTERNS, text)
    if matched_override:
        report.findings.append(
            SafetyFinding(
                "override_attempt",
                "gate_override",
                "Validation states and gates change only when their recorded criteria are met, never because a message asks.",
                matched_override,
            )
        )
    return report


def screen_generated_text(text: str) -> SafetyReport:
    """Run on model output and on generated copy (landing pages, store pages, announcements)."""
    report = SafetyReport()
    for rule, pattern in UNSAFE_OUTPUT_PATTERNS:
        match = pattern.search(text)
        if match:
            report.findings.append(SafetyFinding("unsafe_claim", rule, f"Generated text contained a {rule.replace('_', ' ')}.", match.group(0)))
    return report


def redact_unsafe_sentences(text: str) -> tuple[str, list[str]]:
    """Remove sentences that make prohibited claims; return the cleaned text and the removed rules."""
    removed: list[str] = []
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.?!])\s+", text):
        report = screen_generated_text(sentence)
        if report.blocked:
            removed.extend(report.rules())
        else:
            kept.append(sentence)
    cleaned = " ".join(kept).strip()
    if removed:
        cleaned = (cleaned + " [Removed by Mate's policy guard: " + ", ".join(sorted(set(removed))) + ".]").strip()
    return cleaned, removed


def sanitize_external_text(text: str, limit: int = 1500) -> tuple[str, bool]:
    """Treat retrieved/uploaded text strictly as data: strip control chars and instruction-like content."""
    cleaned = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", " ", text)[: limit * 2]
    flagged = False
    for pattern in INJECTION_PATTERNS:
        if pattern.search(cleaned):
            flagged = True
            cleaned = pattern.sub("[instruction-like text removed]", cleaned)
    return cleaned[:limit].strip(), flagged


def refusal_message(report: SafetyReport) -> str:
    lines: list[str] = []
    seen: set[str] = set()
    for finding in report.findings:
        if finding.message not in seen:
            seen.add(finding.message)
            lines.append(finding.message)
    alternatives = {
        "fake_reviews": "Ask your first real users for honest feedback after they have used the product, and publish only what they agree to share.",
        "fake_signups": "Run the experiment, record the real numbers, and let the gate compare them with the target you declared up front.",
        "gate_override": "If you think a result is wrong, add evidence (with a source) or re-run the experiment; the gate re-evaluates from recorded data.",
        "physical_goods": "If the audience matters to you, we can look for a digital product that serves the same people.",
        "financial_products": "We can explore digital tools adjacent to this audience that do not give financial or investment advice.",
        "crypto": "We can explore non-crypto digital products for the same audience.",
        "health_advice": "We can explore digital tools for this audience that do not give health advice (for example scheduling or content organisation).",
        "legal_advice": "We can explore digital tools for this audience that do not give legal advice.",
    }
    for rule in report.rules():
        if rule in alternatives and alternatives[rule] not in lines:
            lines.append(alternatives[rule])
    return " ".join(lines)
