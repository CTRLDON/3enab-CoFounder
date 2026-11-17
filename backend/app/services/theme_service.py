"""Adaptive theme engine.

The workspace palette follows the *kind of system* the founder is building. The current approved
plan (or, before approval, the latest proposal / starting idea) is classified into a system
archetype with transparent keyword matching; each archetype has an accent hue chosen from
documented conventions for that type of software (see docs/design/adaptive-palettes.md). Every
token is generated in OKLCH and then checked against WCAG 2.x contrast targets in code; colours
are darkened until they pass, so a palette can never ship below AA.

What changes with the plan: the accent hue (archetype) and its saturation (venture state —
a stopped or pivoting venture is visibly muted). What never changes: the economic and evidence
colours, so "amber = expense" means the same thing in every workspace.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.color_math import contrast_ratio, darken_until, oklch_to_hex


@dataclass(frozen=True)
class Archetype:
    key: str
    label: str
    hue: float
    chroma: float
    keywords: tuple[str, ...]
    rationale: str


ARCHETYPES: dict[str, Archetype] = {
    a.key: a
    for a in [
        Archetype(
            "general",
            "No direction yet",
            185,
            0.075,
            (),
            "Before there is a product direction the accent stays a quiet teal, so attention stays on the conversation.",
        ),
        Archetype(
            "learning",
            "Learning and education tools",
            150,
            0.11,
            ("student", "students", "exam", "exams", "course", "courses", "study", "revision", "tutor", "tutoring",
             "school", "university", "learning", "teacher", "teachers", "classroom", "lesson", "quiz", "curriculum", "homework"),
            "Learning tools are used in long, repeated sessions. A mid-chroma green keeps the accent calm for long reading "
            "and stays clearly separate from the amber used for expenses and warnings.",
        ),
        Archetype(
            "b2b_ops",
            "Business operations software",
            250,
            0.12,
            ("crm", "invoice", "invoicing", "inventory", "scheduling", "schedule", "booking", "bookings", "workflow",
             "recruiting", "operations", "smb", "small business", "centers", "centres", "agency", "agencies", "b2b",
             "staff", "attendance", "dashboard", "back-office", "clinic scheduling", "owners"),
            "Operations tools are scanned record by record. Blue is the conventional interactive colour in widely used "
            "business design systems (for example IBM Carbon and Atlassian), so actions read as actions without "
            "competing with status colours.",
        ),
        Archetype(
            "developer",
            "Developer and technical tools",
            278,
            0.13,
            ("developer", "developers", "api", "apis", "sdk", "devops", "code", "coding", "github", "cli", "deploy",
             "programming", "engineers", "open source", "database", "logs", "monitoring"),
            "Developer tools are read like documentation: near-neutral surfaces, dense text and one saturated indigo "
            "accent reserved for actions and links.",
        ),
        Archetype(
            "creator",
            "Creative and content tools",
            2,
            0.12,
            ("content", "creator", "creators", "design", "designers", "video", "music", "podcast", "writing", "writers",
             "caption", "captions", "photo", "photography", "art", "artists", "illustration", "templates", "newsletter"),
            "Creative tools frame the user's own work, so the interface stays neutral and a rose accent marks only "
            "the controls.",
        ),
        Archetype(
            "commerce",
            "Digital commerce and marketplaces",
            38,
            0.12,
            ("marketplace", "store", "shop", "sellers", "buyers", "listing", "listings", "catalog", "catalogue",
             "ecommerce", "e-commerce", "digital downloads", "checkout", "storefront"),
            "Commerce flows centre on one primary step. A warm coral accent singles out that step; its chroma stays "
            "below the expense amber so cost markers remain unambiguous.",
        ),
        Archetype(
            "community",
            "Community and social products",
            212,
            0.10,
            ("community", "communities", "social", "network", "members", "membership", "forum", "club", "clubs",
             "events", "volunteer", "volunteers", "group", "groups", "meetup", "alumni"),
            "Community products are about people and conversation. A cyan accent keeps the space open and stays "
            "distinct from the green used for revenue.",
        ),
        Archetype(
            "lifestyle",
            "Lifestyle and hobby products",
            112,
            0.085,
            ("travel", "recipes", "cooking", "hobby", "hobbies", "gardening", "pets", "fitness tracking", "habits",
             "language learning", "reading", "games", "gaming", "sports"),
            "Lifestyle and hobby products get a soft olive accent with low chroma; it deliberately avoids clinical "
            "palettes, since health-advice products are out of scope.",
        ),
    ]
}

STATE_MODIFIERS: dict[str, tuple[float, str]] = {
    "STOPPED": (0.3, "Muted: the venture is stopped."),
    "PIVOT_REQUIRED": (0.5, "Muted: a pivot is required before work continues."),
}

# Fixed semantic colours (OKLCH): meaning must not change between workspaces.
ECONOMIC = {
    "revenue": (0.52, 0.10, 165),
    "expense": (0.66, 0.14, 70),
    "mixed": (0.52, 0.13, 305),
    "strategic": (0.50, 0.05, 255),
    "unknown": (0.60, 0.0, 0),
}
EVIDENCE = {
    "VERIFIED": (0.50, 0.11, 155),
    "ESTIMATE": (0.50, 0.11, 245),
    "ASSUMPTION": (0.55, 0.12, 70),
    "PROJECTION": (0.50, 0.12, 300),
    "MOCKED": (0.52, 0.17, 25),
    "UNKNOWN": (0.50, 0.0, 0),
}


@dataclass
class Classification:
    archetype: Archetype
    matched_terms: list[str]
    scores: dict[str, float]


def classify_system(weighted_texts: list[tuple[str, float]]) -> Classification:
    scores: dict[str, float] = {key: 0.0 for key in ARCHETYPES if key != "general"}
    matched: dict[str, list[str]] = {key: [] for key in scores}
    for text, weight in weighted_texts:
        lowered = (text or "").lower()
        for key, archetype in ARCHETYPES.items():
            if key == "general":
                continue
            for keyword in archetype.keywords:
                if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                    scores[key] += weight
                    if keyword not in matched[key]:
                        matched[key].append(keyword)
    best = max(scores, key=lambda k: scores[k]) if scores else "general"
    if scores.get(best, 0) <= 0:
        return Classification(ARCHETYPES["general"], [], scores)
    return Classification(ARCHETYPES[best], matched[best][:6], scores)


def _econ_tokens(surface: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name, (lightness, chroma, hue) in ECONOMIC.items():
        stripe, _ = darken_until(lightness, chroma, hue, surface, 3.0)
        soft = oklch_to_hex(0.965, chroma * 0.25, hue)
        text, _ = darken_until(0.45, chroma, hue, soft, 4.5)
        tokens[f"econ-{name}"] = stripe
        tokens[f"econ-{name}-soft"] = soft
        tokens[f"econ-{name}-text"] = text
    return tokens


def _evidence_tokens() -> dict[str, str]:
    tokens: dict[str, str] = {}
    for name, (lightness, chroma, hue) in EVIDENCE.items():
        soft = oklch_to_hex(0.955, chroma * 0.3, hue)
        text, _ = darken_until(lightness, chroma, hue, soft, 4.5)
        tokens[f"ev-{name.lower()}-bg"] = soft
        tokens[f"ev-{name.lower()}-fg"] = text
    return tokens


def build_palette(archetype: Archetype, state: str | None = None) -> dict[str, Any]:
    factor, state_note = STATE_MODIFIERS.get(state or "", (1.0, None))
    hue, chroma = archetype.hue, archetype.chroma * factor

    bg = oklch_to_hex(0.982, 0.006, hue)
    surface = oklch_to_hex(0.997, 0.003, hue)
    sunken = oklch_to_hex(0.958, 0.009, hue)
    border = oklch_to_hex(0.905, 0.01, hue)
    text = oklch_to_hex(0.25, 0.02, hue)
    text_muted, _ = darken_until(0.53, 0.02, hue, sunken, 4.5)
    control_border, _ = darken_until(0.70, 0.015, hue, surface, 3.0)
    accent, accent_l = darken_until(0.56, chroma, hue, "#ffffff", 4.6)
    accent_hover = oklch_to_hex(accent_l - 0.06, chroma, hue)
    accent_soft = oklch_to_hex(0.947, chroma * 0.3, hue)
    accent_text, _ = darken_until(0.52, chroma, hue, accent_soft, 4.5)
    tokens = {
        "bg": bg,
        "surface": surface,
        "surface-sunken": sunken,
        "border": border,
        "control-border": control_border,
        "text": text,
        "text-muted": text_muted,
        "accent": accent,
        "accent-hover": accent_hover,
        "accent-contrast": "#ffffff",
        "accent-soft": accent_soft,
        "accent-text": accent_text,
        "focus": accent,
        "danger": darken_until(0.52, 0.15, 25, surface, 4.5)[0],
        **_econ_tokens(surface),
        **_evidence_tokens(),
    }
    return {"tokens": tokens, "state_note": state_note, "contrast": contrast_report(tokens)}


CONTRAST_CHECKS: list[tuple[str, str, float]] = [
    ("text", "bg", 4.5),
    ("text", "surface-sunken", 4.5),
    ("text-muted", "bg", 4.5),
    ("text-muted", "surface", 4.5),
    ("text-muted", "surface-sunken", 4.5),
    ("accent-contrast", "accent", 4.5),
    ("accent-contrast", "accent-hover", 4.5),
    ("accent-text", "bg", 4.5),
    ("accent-text", "accent-soft", 4.5),
    ("focus", "bg", 3.0),
    ("control-border", "surface", 3.0),
    ("danger", "surface", 4.5),
    *[(f"econ-{n}", "surface", 3.0) for n in ECONOMIC],
    *[(f"econ-{n}-text", f"econ-{n}-soft", 4.5) for n in ECONOMIC],
    *[(f"ev-{n.lower()}-fg", f"ev-{n.lower()}-bg", 4.5) for n in EVIDENCE],
]


def contrast_report(tokens: dict[str, str]) -> list[dict[str, Any]]:
    report = []
    for fg, bg, minimum in CONTRAST_CHECKS:
        ratio = contrast_ratio(tokens[fg], tokens[bg])
        report.append({"foreground": fg, "background": bg, "ratio": round(ratio, 2), "required": minimum, "passes": ratio >= minimum})
    return report


def theme_for(weighted_texts: list[tuple[str, float]], state: str | None, source: str) -> dict[str, Any]:
    classification = classify_system(weighted_texts)
    palette = build_palette(classification.archetype, state)
    return {
        "archetype": classification.archetype.key,
        "label": classification.archetype.label,
        "rationale": classification.archetype.rationale,
        "matched_terms": classification.matched_terms,
        "source": source,
        "state_note": palette["state_note"],
        "tokens": palette["tokens"],
        "contrast": palette["contrast"],
        "all_contrast_checks_pass": all(item["passes"] for item in palette["contrast"]),
    }
